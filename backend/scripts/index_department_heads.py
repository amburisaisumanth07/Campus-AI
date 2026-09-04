"""
Index authoritative MITS Department Heads into ChromaDB.
Associates with official Document #276 in PostgreSQL.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.db.models import Document, DocumentVersion, DocumentPage, DocumentStatus, DocumentType, SourceType
from backend.app.rag import vectorstore, embeddings, pipeline

HOD_URL = "https://mits.ac.in/departmentheads"

HOD_CHUNKS = [
    {
        "title": "MITS Official Department Heads - Complete Directory for all Engineering, Computing & Management Departments",
        "text": """Madanapalle Institute of Technology & Science (MITS) - Official Heads of Departments (All Departments):
- Civil Engineering (CIVIL): Dr. Vijayakumar Natesan (Head – Civil, Profile: https://mits.ac.in/facultyprofile/7)
- Computer Science & Engineering (CSE): Dr. M. Sreedevi (Professor & Head – CSE, Profile: https://mits.ac.in/facultyprofile/140)
- Computer Science & Engineering (AI & ML) (CSE-AIML): Dr. S. Padma (Head – CSE AI and ML, Profile: https://mits.ac.in/facultyprofile/144)
- Computer Science & Engineering (Artificial Intelligence) (AI): Dr. R. Kalpana (Head – CSE Artificial Intelligence, Profile: https://mits.ac.in/facultyprofile/80)
- Computer Science & Engineering (Data Science) (CSE-DS): Dr. S. Kusuma (Head – CSE Data Science, Profile: https://mits.ac.in/facultyprofile/98)
- Computer Science & Engineering (Cyber Security) (CSE-CS): Dr. Brahm Prakash (Head – CSE Cyber Security, Profile: https://mits.ac.in/facultyprofile/1085)
- Computer Science and Technology (CST): Dr. K. Dinesh (Head of Department – CST, Profile: https://mits.ac.in/department/27)
- Electronics & Communication Engineering (ECE): Dr. Sanjay Kumar C. Gowre (Head – ECE, Profile: https://mits.ac.in/facultyprofile/1018)
- Electrical & Electronics Engineering (EEE): Dr. Manavaalan Gunasekaran (Head – EEE, Profile: https://mits.ac.in/facultyprofile/931)
- Mechanical Engineering (MECH): Dr. S. Bhaskaran (Head – Mechanical, Profile: https://mits.ac.in/facultyprofile/306)
- Management Studies (MBA): Dr. R. Varadarajan (Professor & Head - Management Studies, Profile: https://mits.ac.in/school-of-management)
- Computer Applications (MCA): Dr. N. Naveen Kumar (Head – Computer Applications, Profile: https://mits.ac.in/facultyprofile/254)
- Basic Sciences & Humanities (BSH): Dr. R. Saravana (Head (I/c) – Mathematics, Profile: https://mits.ac.in/facultyprofile/351)
Official Source: https://mits.ac.in/departmentheads""",
        "department": "Administration",
    },
    {
        "title": "MITS Official Department Heads - Computing & Engineering (CSE, AIML, AI, DS, CS, CST)",
        "text": """Madanapalle Institute of Technology & Science (MITS) - Official Heads of Departments (Computing Sciences):
1. Department of Computer Science & Engineering (CSE):
   - Head of Department (HOD): Dr. M. Sreedevi
   - Designation: Professor & Head – CSE
   - Department: CSE
   - Profile: https://mits.ac.in/facultyprofile/140

2. Department of Computer Science & Engineering (AI & ML) (CSE-AIML):
   - Head of Department (HOD): Dr. S. Padma
   - Designation: Head – CSE (AI and ML)
   - Department: CSE-AIML
   - Profile: https://mits.ac.in/facultyprofile/144

3. Department of Computer Science & Engineering (Artificial Intelligence) (AI):
   - Head of Department (HOD): Dr. R. Kalpana
   - Designation: Head – CSE (Artificial Intelligence)
   - Department: AI
   - Profile: https://mits.ac.in/facultyprofile/80

4. Department of Computer Science and Engineering (Data Science) (CSE-DS):
   - Head of Department (HOD): Dr. S. Kusuma
   - Designation: Head – CSE (Data Science)
   - Department: CSE-DS
   - Profile: https://mits.ac.in/facultyprofile/98

5. Department of Computer Science and Engineering (Cyber Security) (CSE-CS):
   - Head of Department (HOD): Dr. Brahm Prakash
   - Designation: Head – CSE (Cyber Security)
   - Department: CSE-CS
   - Profile: https://mits.ac.in/facultyprofile/1085

6. Department of Computer Science and Technology (CST):
   - Head of Department (HOD): Dr. K. Dinesh
   - Designation: Head of Department – CST
   - Department: CST
   - Profile: https://mits.ac.in/department/27""",
        "department": "School of Computing",
    },
    {
        "title": "MITS Official Department Heads - Engineering (ECE, EEE, Mechanical, Civil)",
        "text": """Madanapalle Institute of Technology & Science (MITS) - Official Heads of Departments (Core Engineering):
1. Department of Civil Engineering (CIVIL):
   - Head of Department (HOD): Dr. Vijayakumar Natesan
   - Designation: Head – Civil
   - Department: CIVIL
   - Profile: https://mits.ac.in/facultyprofile/7

2. Department of Electronics & Communication Engineering (ECE):
   - Head of Department (HOD): Dr. Sanjay Kumar C. Gowre
   - Designation: Head – ECE
   - Department: ECE
   - Profile: https://mits.ac.in/facultyprofile/1018

3. Department of Electrical & Electronics Engineering (EEE):
   - Head of Department (HOD): Dr. Manavaalan Gunasekaran
   - Designation: Head – EEE
   - Department: EEE
   - Profile: https://mits.ac.in/facultyprofile/931

4. Department of Mechanical Engineering (MECH):
   - Head of Department (HOD): Dr. S. Bhaskaran
   - Designation: Head – Mechanical
   - Department: MECH
   - Profile: https://mits.ac.in/facultyprofile/306""",
        "department": "School of Engineering",
    },
    {
        "title": "MITS Official Department Heads - Management, Computer Applications & Basic Sciences (MBA, MCA, BSH)",
        "text": """Madanapalle Institute of Technology & Science (MITS) - Official Heads of Departments:
1. Department of Management Studies (MBA):
   - Head of Department (HOD): Dr. R. Varadarajan
   - Designation: Professor & Head - Management Studies
   - Department: MBA
   - Profile: https://mits.ac.in/school-of-management

2. Department of Computer Applications (MCA):
   - Head of Department (HOD): Dr. N. Naveen Kumar
   - Designation: Head – Computer Applications
   - Department: MCA
   - Profile: https://mits.ac.in/facultyprofile/254

3. Department of Basic Sciences & Humanities (BSH):
   - Head of Department (HOD): Dr. R. Saravana (Head (I/c) – Mathematics, Profile: 351)
   - Dr. Jagadeesh Babu Bellam (Head (I/c) – Physics, Profile: 375)
   - Dr. Renjith Bhaskaran (Head – Chemistry, Profile: 377)
   - Dr. Sudhakar Beedam (Head (I/c) – English & Foreign Languages, Profile: 691)
   - Department: BSH""",
        "department": "Administration",
    },
]


def index_heads():
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.source_url == HOD_URL).first()
        if not doc:
            doc = Document(
                title="MITS Official Department Heads Directory",
                filename="departmentheads.html",
                document_type=DocumentType.DEPARTMENT_DOCUMENT,
                source_type=SourceType.OFFICIAL_WEBSITE,
                source_url=HOD_URL,
                status=DocumentStatus.READY,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

        doc_id = doc.id
        print(f"[+] Using PostgreSQL Document ID {doc_id} for {HOD_URL}")

        col = vectorstore.get_collection()

        # Delete any legacy or doc_999 chunks
        col.delete(where={"source_url": HOD_URL})
        try:
            col.delete(ids=["doc_999_chunk_0", "doc_999_chunk_1"])
        except Exception:
            pass

        # Prepare chunk records
        records = []
        texts = []
        for idx, item in enumerate(HOD_CHUNKS):
            cid = f"doc_{doc_id}_chunk_{idx}"
            txt = item["text"].strip()
            texts.append(txt)
            records.append({
                "id": cid,
                "chunk_id": cid,
                "text": txt,
                "metadata": {
                    "document_id": doc_id,
                    "doc_id": doc_id,
                    "title": item["title"],
                    "department": item["department"],
                    "academic_year": "2026-2027",
                    "document_type": "DEPARTMENT_DOCUMENT",
                    "source_type": "OFFICIAL_WEBSITE",
                    "source_url": HOD_URL,
                    "page_number": 1,
                    "source_pages": "1",
                    "chunk_index": idx,
                }
            })

        print(f"[+] Generating embeddings for {len(texts)} authoritative HOD chunks...")
        embeddings_list = embeddings.embed_documents(texts)
        count = vectorstore.add_chunks(records, embeddings_list)
        print(f"[SUCCESS] Upserted {count} chunks for Department Heads into ChromaDB.")

        # Invalidate pipeline cache so new chunks take effect immediately
        pipeline.clear_rag_cache()
    finally:
        db.close()


if __name__ == "__main__":
    index_heads()
