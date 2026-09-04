"""
Pydantic schemas for MITS Official Entities.
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    category: str
    published_date: Optional[datetime] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    document_url: Optional[str] = None
    source_name: str
    is_valid: bool = True
    last_verified_at: Optional[datetime] = None
    created_at: datetime


class AcademicCalendarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year: str
    program: str
    year: Optional[str] = None
    semester: Optional[str] = None
    event_name: str
    event_description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    document_url: Optional[str] = None
    source_name: str
    is_valid: bool = True
    last_verified_at: Optional[datetime] = None
    created_at: datetime


class ExaminationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    exam_type: str
    program: Optional[str] = None
    year: Optional[str] = None
    semester: Optional[str] = None
    published_date: Optional[datetime] = None
    exam_date: Optional[datetime] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    document_url: Optional[str] = None
    source_name: str
    is_valid: bool = True
    last_verified_at: Optional[datetime] = None
    created_at: datetime


class FacultyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    designation: Optional[str] = None
    qualification: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_url: Optional[str] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    is_valid: bool = True
    last_verified_at: Optional[datetime] = None
    created_at: datetime


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    school: Optional[str] = None
    description: Optional[str] = None
    hod: Optional[str] = None
    hod_name: Optional[str] = None
    hod_designation: Optional[str] = None
    hod_profile_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    faculty: Optional[str] = None
    programs: Optional[str] = None
    courses: Optional[str] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    is_valid: bool = True
    last_verified_at: Optional[datetime] = None
    created_at: datetime


class PlacementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    job_role: Optional[str] = None
    drive_date: Optional[datetime] = None
    eligibility: Optional[str] = None
    description: Optional[str] = None
    package_details: Optional[str] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    document_url: Optional[str] = None
    is_valid: bool = True
    last_verified_at: Optional[datetime] = None
    created_at: datetime


class CollegeInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    title: str
    content: str
    category: str
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    is_valid: bool = True
    last_verified_at: Optional[datetime] = None


class ImportantLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    url: str
    canonical_url: Optional[str] = None
    category: str
    icon: Optional[str] = None
    display_order: int
    is_valid: bool = True
    is_active: bool
    last_verified_at: Optional[datetime] = None


class SearchResultItem(BaseModel):
    id: int
    type: str  # announcement, calendar, examination, department, placement, document, faculty
    title: str
    category: Optional[str] = None
    date: Optional[datetime] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    canonical_url: Optional[str] = None
    is_valid: bool = True
    link_url: str


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
