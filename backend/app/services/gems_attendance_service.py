"""
Official MITS GEMS Attendance Adapter Service.

Interacts with the official MITS GEMS Student Information / Attendance Portal
(http://mitsims.in/) to retrieve verified student attendance in an isolated,
ephemeral in-memory session.

Security Invariants:
- NEVER persist or log student passwords in plaintext, database, or logs.
- Strict session lifecycle management: in-memory session only.
- Session is automatically closed and logout requested upon completion.
- Credentials and cookies are explicitly purged from memory.
- Passwords are never sent to Gemini, ChromaDB, or frontend storage.
"""
import ast
from datetime import datetime, timezone
import html
import json
import math
import re
from typing import Dict, Any, Optional, List, Tuple
import urllib.parse
import httpx

from backend.app.core.logging import logger
from backend.app.services.attendance_service import (
    AttendanceIntegrationError,
    AttendanceAuthError,
    AttendancePortalUnavailableError,
    AttendanceMalformedResponseError,
    MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE,
    calculate_subject_percentage,
    calculate_overall_percentage,
    determine_attendance_status,
    calculate_classes_can_miss,
    calculate_classes_required,
)

GEMS_BASE_URL = "http://mitsims.in"


def safe_parse_gems_json(text: str) -> Dict[str, Any]:
    """
    Safely parse standard JSON or relaxed Struts/ExtJS JavaScript object literals
    WITHOUT using unsafe eval().
    """
    if not text or not text.strip():
        raise AttendanceMalformedResponseError("Could not read attendance data from MITS GEMS.")

    cleaned = text.strip()

    # Step 1: Strip wrapping parentheses and trailing semicolons
    while (cleaned.startswith("(") and cleaned.endswith(")")) or cleaned.endswith(";"):
        if cleaned.endswith(";"):
            cleaned = cleaned[:-1].strip()
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = cleaned[1:-1].strip()

    # Step 2: Try standard JSON
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Step 3: Strip JS comments
    no_comments = re.sub(r'//.*?$|/\*.*?\*/', '', cleaned, flags=re.MULTILINE | re.DOTALL).strip()
    while (no_comments.startswith("(") and no_comments.endswith(")")) or no_comments.endswith(";"):
        if no_comments.endswith(";"):
            no_comments = no_comments[:-1].strip()
        if no_comments.startswith("(") and no_comments.endswith(")"):
            no_comments = no_comments[1:-1].strip()

    try:
        return json.loads(no_comments)
    except Exception:
        pass

    # Step 4: Safe Abstract Syntax Tree (AST) static parser (no code execution)
    try:
        tree = ast.parse(f"__val__ = {no_comments}")

        def _node_to_dict(node):
            if isinstance(node, ast.Dict):
                d = {}
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Name):
                        key_str = k.id
                    elif isinstance(k, ast.Constant):
                        key_str = str(k.value)
                    else:
                        key_str = str(_node_to_dict(k))
                    d[key_str] = _node_to_dict(v)
                return d
            elif isinstance(node, (ast.List, ast.Tuple)):
                return [_node_to_dict(elt) for elt in node.elts]
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                lower_id = node.id.lower()
                if lower_id == 'true': return True
                if lower_id == 'false': return False
                if lower_id in ('null', 'undefined', 'none'): return None
                return node.id
            elif isinstance(node, ast.UnaryOp):
                operand = _node_to_dict(node.operand)
                if isinstance(node.op, ast.USub) and isinstance(operand, (int, float)):
                    return -operand
                return operand
            else:
                return None

        result = _node_to_dict(tree.body[0].value)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    # Step 5: Relaxed JSON regex normalizer fallback
    try:
        def quote_key(m):
            prefix = m.group(1)
            key = m.group(2)
            return f'{prefix}"{key}":'

        normalized = re.sub(r'([{,\s])([a-zA-Z0-9_$]+)\s*:', quote_key, no_comments)

        def replace_single_quotes(m):
            content = m.group(1)
            escaped_content = content.replace('\\"', '"').replace('"', '\\"')
            return f'"{escaped_content}"'

        normalized = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", replace_single_quotes, normalized)
        normalized = re.sub(r',\s*([}\]])', r'\1', normalized)
        normalized = re.sub(r':\s*undefined\b', ': null', normalized)

        return json.loads(normalized)
    except Exception:
        raise AttendanceMalformedResponseError("Could not read attendance data from MITS GEMS.")


def clean_html_value(val: Any) -> str:
    """Strip HTML tags, unescape HTML entities, and normalize whitespace."""
    if not isinstance(val, str):
        return str(val) if val is not None else ""
    # remove html tags
    plain = re.sub(r"<[^>]+>", " ", val)
    # unescape entities like &nbsp;, &amp;
    plain = html.unescape(plain)
    # normalize spaces and remove embedded tabs
    return " ".join(plain.replace("\t", " ").split())


class GemsAttendanceAdapter:
    """Official MITS GEMS Attendance Integrator."""

    def __init__(self, base_url: str = GEMS_BASE_URL, timeout_seconds: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    def validate_roll_number(self, roll_number: str) -> str:
        """Validate and normalize MITS student roll number."""
        if not roll_number:
            raise AttendanceIntegrationError(
                "Roll number is required.",
                error_type="MISSING_ROLL_NUMBER",
                status_code=400
            )
        cleaned = roll_number.strip().upper()
        # Accept valid alphanumeric roll numbers (e.g. 24691A31N1, 21691A0501)
        if not re.match(r"^[A-Z0-9/-]{2,20}$", cleaned):
            raise AttendanceIntegrationError(
                "Invalid MITS roll number format.",
                error_type="INVALID_ROLL_NUMBER",
                status_code=400
            )
        return cleaned

    def _extract_from_form_panel(
        self, data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Extract real student attendance records from ExtJS formPanel fieldsets
        (specifically 'semesterActivity' for rows and 'SubDetails' for subject names).
        """
        form_panel = data.get("formPanel")
        if not isinstance(form_panel, dict) and "content" in data and isinstance(data["content"], dict):
            form_panel = data["content"].get("formPanel")

        if not isinstance(form_panel, dict):
            return [], None

        fp_items = form_panel.get("items", [])
        if not isinstance(fp_items, list):
            return [], None

        sub_details_item = None
        sem_activity_item = None

        for it in fp_items:
            if not isinstance(it, dict):
                continue
            it_id = str(it.get("id") or "").lower()
            title = str(it.get("title") or "").lower()
            if it_id == "subdetails":
                sub_details_item = it
            elif it_id == "semesteractivity" or "semester activity" in title:
                sem_activity_item = it

        # 1. Map Subject Code -> Full Subject Name from SubDetails
        subject_names: Dict[str, str] = {}
        if sub_details_item and isinstance(sub_details_item.get("items"), list):
            for row in sub_details_item["items"]:
                if not isinstance(row, dict) or not isinstance(row.get("items"), list):
                    continue
                vals = [clean_html_value(col.get("value")) for col in row["items"] if isinstance(col, dict)]
                # SubDetails columns: S.NO, CODE, SUBJECT, FACULTY, THEORY CREDITS, LAB CREDITS
                if len(vals) >= 3 and vals[0].isdigit():
                    code = vals[1].upper()
                    name = vals[2]
                    if code and name:
                        subject_names[code] = name

        detected_semester = None
        subjects: List[Dict[str, Any]] = []

        # 2. Extract attendance records from semesterActivity
        if sem_activity_item:
            raw_title = sem_activity_item.get("title") or ""
            if "for-" in raw_title:
                detected_semester = raw_title.split("for-", 1)[1].strip()
            elif "for" in raw_title:
                detected_semester = raw_title.split("for", 1)[1].strip()
            elif raw_title:
                detected_semester = raw_title.strip()

            rows = sem_activity_item.get("items", [])
            if isinstance(rows, list):
                code_col = 1
                att_col = 2
                tot_col = 3
                pct_col = 4

                for row in rows:
                    if not isinstance(row, dict) or not isinstance(row.get("items"), list):
                        continue
                    vals = [clean_html_value(col.get("value")) for col in row["items"] if isinstance(col, dict)]
                    if not vals:
                        continue

                    # Dynamic header inspection
                    joined_header = " ".join(v.upper() for v in vals)
                    if "SUBJECT" in joined_header or "ATTENDED" in joined_header:
                        for i, h in enumerate(vals):
                            hu = h.upper()
                            if "CODE" in hu or "SUBJECT" in hu:
                                code_col = i
                            elif "ATTENDED" in hu:
                                att_col = i
                            elif "CONDUCTED" in hu or "TOTAL" in hu:
                                tot_col = i
                            elif "%" in hu or "PERCENTAGE" in hu:
                                pct_col = i
                        continue

                    # Data row validation: S.NO must be numeric
                    if vals[0].isdigit() and len(vals) > max(code_col, att_col, tot_col):
                        raw_code = vals[code_col]
                        clean_code = raw_code.strip()
                        if not clean_code:
                            continue

                        clean_name = subject_names.get(clean_code.upper(), clean_code)

                        try:
                            attended = int(float(vals[att_col]))
                        except (ValueError, TypeError):
                            continue  # Skip malformed row

                        try:
                            total = int(float(vals[tot_col]))
                        except (ValueError, TypeError):
                            continue  # Skip malformed row

                        # Validation: attended >= 0, total > 0, attended <= total
                        if attended < 0 or total <= 0 or attended > total:
                            logger.warning(
                                f"[GEMS_ROW_VALIDATION_FAILED] Code={clean_code} attended={attended} total={total}"
                            )
                            continue  # Skip malformed row

                        # Calculate accurate percentage
                        pct = round((attended / total * 100.0), 2)

                        # If GEMS supplied percentage, validate within reasonable tolerance
                        if len(vals) > pct_col and vals[pct_col]:
                            try:
                                reported_pct = float(vals[pct_col].replace("%", "").strip())
                                if abs(reported_pct - pct) <= 2.0:
                                    pct = reported_pct
                            except (ValueError, TypeError):
                                pass

                        subjects.append({
                            "code": clean_code,
                            "name": clean_name,
                            "attended": attended,
                            "total": total,
                            "percentage": pct,
                            "semester": detected_semester,
                        })

        return subjects, detected_semester

    def _extract_from_raw_text(
        self, text: str
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fallback regex extractor that parses ExtJS fieldsets directly from raw text."""
        sub_pos = text.find("id:'SubDetails'")
        if sub_pos == -1:
            sub_pos = text.find('id:"SubDetails"')
        sem_pos = text.find("id:'semesterActivity'")
        if sem_pos == -1:
            sem_pos = text.find('id:"semesterActivity"')
        attn_pos = text.find("id:'attnFldSet'")
        if attn_pos == -1:
            attn_pos = text.find('id:"attnFldSet"')

        if sem_pos == -1:
            return [], None

        def extract_fieldset_rows(block_text: str) -> List[List[str]]:
            # Extract each row block with bottom-border (not bottom-border-header)
            row_blocks = re.findall(
                r"componentCls\s*:\s*['\"]bottom-border['\"].*?items\s*:\s*\[(.*?)\]",
                block_text,
                re.DOTALL
            )
            rows = []
            for rb in row_blocks:
                raw_vals = re.findall(
                    r"value\s*:\s*(?:Ext\.String\.format\()?('[\s\S]*?'|\"[\s\S]*?\")", rb
                )
                cleaned = [clean_html_value(rv[1:-1]) for rv in raw_vals]
                if cleaned:
                    rows.append(cleaned)
            # Fallback if bracket notation was different
            if not rows:
                fieldsets = re.split(r"xtype\s*:\s*['\"]fieldset['\"]", block_text)
                for fs in fieldsets:
                    if "bottom-border" not in fs:
                        continue
                    raw_vals = re.findall(
                        r"value\s*:\s*(?:Ext\.String\.format\()?('[\s\S]*?'|\"[\s\S]*?\")", fs
                    )
                    cleaned = [clean_html_value(rv[1:-1]) for rv in raw_vals]
                    if cleaned:
                        rows.append(cleaned)
            return rows

        subject_names = {}
        if sub_pos != -1:
            end_sub = sem_pos if sem_pos > sub_pos else len(text)
            sub_rows = extract_fieldset_rows(text[sub_pos:end_sub])
            for r in sub_rows:
                if len(r) >= 3 and r[0].isdigit():
                    code = r[1].strip().upper()
                    name = r[2].strip()
                    if code and name:
                        subject_names[code] = name

        end_sem = attn_pos if attn_pos > sem_pos else min(len(text), sem_pos + 100000)
        sem_block = text[sem_pos:end_sem]

        detected_semester = None
        title_m = re.search(r"title\s*:\s*['\"]([^'\"]+)['\"]", sem_block[:500])
        if title_m:
            raw_title = title_m.group(1)
            if "for-" in raw_title:
                detected_semester = raw_title.split("for-", 1)[1].strip()
            elif "for" in raw_title:
                detected_semester = raw_title.split("for", 1)[1].strip()
            else:
                detected_semester = raw_title.strip()

        sem_rows = extract_fieldset_rows(sem_block)
        subjects = []
        for r in sem_rows:
            if len(r) >= 5 and r[0].isdigit():
                clean_code = r[1].strip()
                if not clean_code:
                    continue
                clean_name = subject_names.get(clean_code.upper(), clean_code)
                try:
                    attended = int(float(r[2]))
                    total = int(float(r[3]))
                except (ValueError, TypeError):
                    continue
                if attended < 0 or total <= 0 or attended > total:
                    continue
                pct = round((attended / total * 100.0), 2)
                try:
                    rep_pct = float(r[4].replace("%", "").strip())
                    if abs(rep_pct - pct) <= 2.0:
                        pct = rep_pct
                except (ValueError, TypeError):
                    pass

                subjects.append({
                    "code": clean_code,
                    "name": clean_name,
                    "attended": attended,
                    "total": total,
                    "percentage": pct,
                    "semester": detected_semester,
                })

        return subjects, detected_semester

    def _extract_from_legacy_grid(
        self, data: Dict[str, Any], detected_semester: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Extract attendance records from legacy attendanceTable grid format."""
        attn_table = None
        if isinstance(data, dict):
            if "attendanceTable" in data and isinstance(data["attendanceTable"], dict):
                attn_table = data["attendanceTable"]
            elif "content" in data and isinstance(data["content"], dict) and "attendanceTable" in data["content"] and isinstance(data["content"]["attendanceTable"], dict):
                attn_table = data["content"]["attendanceTable"]
            else:
                for k, v in data.items():
                    if isinstance(v, dict):
                        if "attendance" in k.lower() or "attgrid" in k.lower():
                            attn_table = v
                            break
                        for sub_k, sub_v in v.items():
                            if isinstance(sub_v, dict) and ("attendance" in sub_k.lower() or "attgrid" in sub_k.lower()):
                                attn_table = sub_v
                                break
                    if attn_table:
                        break

        raw_records = []
        schema_fields = []
        if isinstance(attn_table, dict):
            raw_records = (
                attn_table.get("records")
                or attn_table.get("data")
                or attn_table.get("rows")
                or attn_table.get("items")
                or []
            )
            schema_fields = [
                f.get("name")
                for f in attn_table.get("schema", {}).get("fields", [])
                if isinstance(f, dict) and f.get("name")
            ]
        elif isinstance(data, dict):
            if "records" in data and isinstance(data["records"], list):
                raw_records = data["records"]
            elif "subjects" in data and isinstance(data["subjects"], list):
                raw_records = data["subjects"]
            elif "data" in data and isinstance(data["data"], list):
                raw_records = data["data"]

        subjects = []
        sem = detected_semester

        for rec in raw_records:
            if isinstance(rec, dict):
                code = str(rec.get("subCode") or rec.get("code") or rec.get("subjectCode") or rec.get("courseCode") or "").strip()
                name = str(rec.get("subName") or rec.get("name") or rec.get("subjectName") or rec.get("courseName") or "Subject").strip()
                try:
                    attended = int(rec.get("classesAttended") or rec.get("attended") or rec.get("present") or rec.get("attendedClasses") or 0)
                except (ValueError, TypeError):
                    attended = 0
                try:
                    total = int(rec.get("classesConducted") or rec.get("total") or rec.get("conducted") or rec.get("totalClasses") or 0)
                except (ValueError, TypeError):
                    total = 0
                rec_sem = rec.get("semester") or rec.get("sem")
                if rec_sem and not sem:
                    sem = str(rec_sem)
            elif isinstance(rec, (list, tuple)) and schema_fields:
                rec_dict = dict(zip(schema_fields, rec))
                code = str(rec_dict.get("subCode") or rec_dict.get("code") or "").strip()
                name = str(rec_dict.get("subName") or rec_dict.get("name") or "Subject").strip()
                try:
                    attended = int(rec_dict.get("classesAttended") or rec_dict.get("attended") or 0)
                except (ValueError, TypeError):
                    attended = 0
                try:
                    total = int(rec_dict.get("classesConducted") or rec_dict.get("total") or 0)
                except (ValueError, TypeError):
                    total = 0
                rec_sem = rec_dict.get("semester")
                if rec_sem and not sem:
                    sem = str(rec_sem)
            else:
                continue

            if total <= 0 or attended < 0 or attended > total:
                continue

            pct = calculate_subject_percentage(attended, total)
            subjects.append({
                "code": code,
                "name": name,
                "attended": attended,
                "total": total,
                "percentage": pct,
                "semester": sem,
            })

        return subjects, sem

    def _normalize_attendance_records(
        self,
        valid_roll: str,
        student_name: str,
        data: Dict[str, Any],
        raw_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Normalize extracted GEMS attendance table into standard CampusAI model."""
        if isinstance(data, dict) and isinstance(data.get("content"), str):
            try:
                parsed_c = safe_parse_gems_json(data["content"])
                if isinstance(parsed_c, dict):
                    data = parsed_c
            except Exception:
                pass

        subjects: List[Dict[str, Any]] = []
        detected_semester: Optional[str] = None

        # 1. Primary: Extract from ExtJS formPanel (semesterActivity & SubDetails)
        fp_subjects, fp_sem = self._extract_from_form_panel(data)
        if fp_subjects:
            subjects = fp_subjects
            detected_semester = fp_sem

        # 2. Secondary fallback: Extract via regex from raw_text
        if not subjects and raw_text:
            rt_subjects, rt_sem = self._extract_from_raw_text(raw_text)
            if rt_subjects:
                subjects = rt_subjects
                detected_semester = rt_sem

        # 3. Tertiary fallback: Extract from legacy grid format
        if not subjects:
            lg_subjects, lg_sem = self._extract_from_legacy_grid(data, detected_semester)
            if lg_subjects:
                subjects = lg_subjects
                if lg_sem:
                    detected_semester = lg_sem

        # 4. If zero subject records are extracted, raise AttendanceMalformedResponseError
        if not subjects:
            raise AttendanceMalformedResponseError(
                "No attendance records were returned by MITS GEMS."
            )

        # Calculate overall attendance strictly as sum(attended) / sum(total) * 100
        overall = calculate_overall_percentage(subjects)
        status_label = determine_attendance_status(overall, required=MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE)

        total_attended = sum(s["attended"] for s in subjects)
        total_classes = sum(s["total"] for s in subjects)
        absent_classes = max(0, total_classes - total_attended)
        is_safe = overall >= MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE
        status_text = (
            "Attendance requirement currently satisfied."
            if is_safe
            else "Attendance is below the required threshold."
        )

        now_formatted = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")

        return {
            # Canonical CampusAI Model
            "student": student_name,
            "roll_number": valid_roll,
            "overall": overall,
            "required": MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE,
            "status": status_label,
            "subjects": subjects,
            "semester": detected_semester,
            # Compatibility properties for UI components
            "student_name": student_name,
            "overall_percentage": overall,
            "attended_classes": total_attended,
            "total_classes": total_classes,
            "absent_classes": absent_classes,
            "required_percentage": MINIMUM_REQUIRED_ATTENDANCE_PERCENTAGE,
            "is_safe": is_safe,
            "status_text": status_text,
            "official_source": self.base_url,
            "last_updated": now_formatted,
            "last_synced": now_formatted,
            "success": True,
        }

    async def fetch_attendance(
        self,
        roll_number: str,
        password: str,
        http_client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """
        Securely query GEMS student attendance asynchronously.
        Password is never logged, persisted, or stored outside this volatile frame.
        """
        valid_roll = self.validate_roll_number(roll_number)
        if not password or len(password.strip()) == 0:
            raise AttendanceIntegrationError(
                "Student password is required.",
                error_type="MISSING_PASSWORD",
                status_code=400
            )

        # SECURITY: Log sanitized roll number only; NEVER log password
        logger.info(f"[GEMS_QUERY] Initiating attendance check for roll_number={valid_roll}")

        client_provided = http_client is not None
        expected_host = urllib.parse.urlparse(self.base_url).netloc.lower()

        def _validate_redirect(response: httpx.Response):
            if response.is_redirect and "location" in response.headers:
                loc = response.headers["location"].strip()
                parsed = urllib.parse.urlparse(loc)
                if parsed.netloc and parsed.netloc.lower() != expected_host:
                    logger.error(f"[SECURITY_ALERT] Blocked foreign redirect attempt to {parsed.netloc}")
                    raise AttendancePortalUnavailableError("External redirect prohibited for GEMS.")

        client = http_client or httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            event_hooks={"response": [_validate_redirect]}
        )

        try:
            # Step 1: Login
            login_url = f"{self.base_url}/studentLogin/studentLogin.action?personType=student"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/",
                "Origin": self.base_url,
            }
            payload = {
                "userId": valid_roll,
                "password": password,
            }

            try:
                login_resp = await client.post(login_url, data=payload, headers=headers)
            except httpx.TimeoutException:
                logger.warning(f"[GEMS_TIMEOUT] Portal timed out during login for roll_number={valid_roll}")
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")
            except httpx.RequestError as exc:
                logger.warning(f"[GEMS_CONN_ERR] Connection failed for roll_number={valid_roll}: {type(exc).__name__}")
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            if login_resp.status_code in (401, 403):
                raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            if login_resp.status_code >= 500:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            login_text = login_resp.text
            # Parse login response
            try:
                login_data = safe_parse_gems_json(login_text)
            except Exception:
                login_data = {}

            if isinstance(login_data, dict):
                if login_data.get("status") == "fail":
                    raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")
                if login_data.get("status") not in ("success", "message") and "invalid" in login_text.lower():
                    raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            if "invalid user id" in login_text.lower() or "invalid password" in login_text.lower() or "incorrect" in login_text.lower():
                raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            # Step 2: Fetch student name / metadata (optional sidebar)
            student_name = "MITS Student"
            try:
                sidebar_url = f"{self.base_url}/gemsonline-student/getLeftSideBar.action?"
                sb_resp = await client.get(sidebar_url, headers=headers)
                if sb_resp.status_code == 200:
                    sb_data = safe_parse_gems_json(sb_resp.text)
                    if isinstance(sb_data, dict) and sb_data.get("studName"):
                        student_name = sb_data["studName"].strip()
            except Exception:
                pass  # Fall back to default student name

            # Step 3: Fetch Attendance Dashboard
            dash_url = f"{self.base_url}/gemsonline-student/dashboard.action?actionType=view"
            dash_headers = {
                "User-Agent": headers["User-Agent"],
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/studentIndex.html",
            }

            try:
                dash_resp = await client.get(dash_url, headers=dash_headers)
            except httpx.TimeoutException:
                logger.warning(f"[GEMS_TIMEOUT] Portal timed out during dashboard fetch for roll_number={valid_roll}")
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")
            except httpx.RequestError as exc:
                logger.warning(f"[GEMS_CONN_ERR] Dashboard request failed: {type(exc).__name__}")
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            if dash_resp.status_code in (401, 403):
                raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            if dash_resp.status_code >= 500:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            dash_text = dash_resp.text

            if "due to inactivity" in dash_text.lower():
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            dash_data = safe_parse_gems_json(dash_text)
            return self._normalize_attendance_records(
                valid_roll, student_name, dash_data, raw_text=dash_text
            )

        finally:
            # Step 4: Logout & Cleanup session
            try:
                logout_url = f"{self.base_url}/studentLogin/studentLogout.action"
                await client.post(logout_url, headers={"User-Agent": "Mozilla/5.0"})
            except Exception:
                pass

            if not client_provided:
                await client.aclose()

            # Ensure local reference to password is deleted
            del password

    def fetch_attendance_sync(
        self,
        roll_number: str,
        password: str,
        http_client: Optional[httpx.Client] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version for test harnesses or synchronous route dependencies.
        """
        valid_roll = self.validate_roll_number(roll_number)
        if not password or len(password.strip()) == 0:
            raise AttendanceIntegrationError(
                "Student password is required.",
                error_type="MISSING_PASSWORD",
                status_code=400
            )

        logger.info(f"[GEMS_QUERY_SYNC] Initiating attendance check for roll_number={valid_roll}")

        client_provided = http_client is not None
        expected_host = urllib.parse.urlparse(self.base_url).netloc.lower()

        def _validate_redirect_sync(response: httpx.Response):
            if response.is_redirect and "location" in response.headers:
                loc = response.headers["location"].strip()
                parsed = urllib.parse.urlparse(loc)
                if parsed.netloc and parsed.netloc.lower() != expected_host:
                    logger.error(f"[SECURITY_ALERT] Blocked foreign redirect attempt to {parsed.netloc}")
                    raise AttendancePortalUnavailableError("External redirect prohibited for GEMS.")

        client = http_client or httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            event_hooks={"response": [_validate_redirect_sync]}
        )

        try:
            login_url = f"{self.base_url}/studentLogin/studentLogin.action?personType=student"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/",
                "Origin": self.base_url,
            }
            payload = {
                "userId": valid_roll,
                "password": password,
            }

            try:
                login_resp = client.post(login_url, data=payload, headers=headers)
            except httpx.TimeoutException:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")
            except httpx.RequestError:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            if login_resp.status_code in (401, 403):
                raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            if login_resp.status_code >= 500:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            login_text = login_resp.text
            try:
                login_data = safe_parse_gems_json(login_text)
            except Exception:
                login_data = {}

            if isinstance(login_data, dict):
                if login_data.get("status") == "fail":
                    raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")
                if login_data.get("status") not in ("success", "message") and "invalid" in login_text.lower():
                    raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            if "invalid user id" in login_text.lower() or "invalid password" in login_text.lower():
                raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            student_name = "MITS Student"
            try:
                sidebar_url = f"{self.base_url}/gemsonline-student/getLeftSideBar.action?"
                sb_resp = client.get(sidebar_url, headers=headers)
                if sb_resp.status_code == 200:
                    sb_data = safe_parse_gems_json(sb_resp.text)
                    if isinstance(sb_data, dict) and sb_data.get("studName"):
                        student_name = sb_data["studName"].strip()
            except Exception:
                pass

            dash_url = f"{self.base_url}/gemsonline-student/dashboard.action?actionType=view"
            dash_headers = {
                "User-Agent": headers["User-Agent"],
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/studentIndex.html",
            }

            try:
                dash_resp = client.get(dash_url, headers=dash_headers)
            except httpx.TimeoutException:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")
            except httpx.RequestError:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            if dash_resp.status_code in (401, 403):
                raise AttendanceAuthError("Invalid MITS GEMS roll number or password.")

            if dash_resp.status_code >= 500:
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            dash_text = dash_resp.text
            if "due to inactivity" in dash_text.lower():
                raise AttendancePortalUnavailableError("Unable to connect to MITS GEMS right now. Please try again later.")

            dash_data = safe_parse_gems_json(dash_text)
            return self._normalize_attendance_records(
                valid_roll, student_name, dash_data, raw_text=dash_text
            )

        finally:
            try:
                logout_url = f"{self.base_url}/studentLogin/studentLogout.action"
                client.post(logout_url, headers={"User-Agent": "Mozilla/5.0"})
            except Exception:
                pass

            if not client_provided:
                client.close()

            del password
