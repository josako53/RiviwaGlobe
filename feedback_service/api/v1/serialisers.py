"""
api/v1/serialisers.py
────────────────────────────────────────────────────────────────────────────
All output serialisers for feedback_service API responses.
Each function takes a model instance → returns a plain dict.

Anonymity enforcement is applied here as the final gatekeeper:
when is_anonymous=True all identity fields return None regardless of
what is stored in the DB.
"""
from __future__ import annotations

from models.feedback import (
    EscalationRequest,
    Feedback,
    FeedbackAction,
    FeedbackAppeal,
    FeedbackCategoryDef,
    FeedbackEscalation,
    FeedbackResolution,
    GrievanceCommittee,
    GrievanceCommitteeMember,
)
from models.feedback import ChannelSession


def feedback_out(f: Feedback) -> dict:
    anon = f.is_anonymous
    return {
        "id":             str(f.id),
        "unique_ref":     f.unique_ref,
        "project_id":     str(f.project_id),
        "stage_id":       str(f.stage_id) if f.stage_id else None,
        "service_location_id": str(f.service_location_id) if f.service_location_id else None,
        "feedback_type":  f.feedback_type,
        "category":       f.category,
        "status":         f.status,
        "priority":       f.priority,
        "current_level":  f.current_level,
        "channel":        f.channel,
        "submission_method": f.submission_method,
        "is_anonymous":   True if anon else False,
        # Identity — all null for anonymous submissions
        "submitted_by_user_id":        None if anon else (str(f.submitted_by_user_id) if f.submitted_by_user_id else None),
        "submitted_by_stakeholder_id": None if anon else (str(f.submitted_by_stakeholder_id) if f.submitted_by_stakeholder_id else None),
        "submitted_by_contact_id":     None if anon else (str(f.submitted_by_contact_id) if f.submitted_by_contact_id else None),
        "submitter_name":              None if anon else f.submitter_name,
        "submitter_phone":             None if anon else f.submitter_phone,
        "submitter_location_lga":      None if anon else f.submitter_location_lga,
        "submitter_location_ward":     None if anon else f.submitter_location_ward,
        "channel_session_id":          None if anon else (str(f.channel_session_id) if f.channel_session_id else None),
        "entered_by_user_id":          None if anon else (str(f.entered_by_user_id) if f.entered_by_user_id else None),
        # Non-identity fields
        "stakeholder_engagement_id":   str(f.stakeholder_engagement_id) if f.stakeholder_engagement_id else None,
        "distribution_id":             str(f.distribution_id)           if f.distribution_id           else None,
        "assigned_committee_id":       str(f.assigned_committee_id)     if f.assigned_committee_id     else None,
        "assigned_to_user_id":         str(f.assigned_to_user_id)       if f.assigned_to_user_id       else None,
        "subject":        f.subject,
        "description":    f.description,
        "media_urls":     f.media_urls,
        "issue_location_description": f.issue_location_description,
        "issue_lga":      f.issue_lga,
        "issue_ward":     f.issue_ward,
        "issue_gps_lat":  f.issue_gps_lat,
        "issue_gps_lng":  f.issue_gps_lng,
        "date_of_incident":       f.date_of_incident.isoformat()       if f.date_of_incident       else None,
        "submitted_at":           f.submitted_at.isoformat(),
        "acknowledged_at":        f.acknowledged_at.isoformat()        if f.acknowledged_at        else None,
        "resolved_at":            f.resolved_at.isoformat()            if f.resolved_at            else None,
        "target_resolution_date": f.target_resolution_date.isoformat() if f.target_resolution_date else None,
        "closed_at":              f.closed_at.isoformat()              if f.closed_at              else None,
    }


def action_out(a: FeedbackAction) -> dict:
    return {
        "id":              str(a.id),
        "action_type":     a.action_type,
        "description":     a.description,
        "is_internal":     a.is_internal,
        "response_method": a.response_method,
        "response_summary": a.response_summary,
        "performed_by_user_id": str(a.performed_by_user_id) if a.performed_by_user_id else None,
        "performed_at":    a.performed_at.isoformat(),
    }


def esc_out(e: FeedbackEscalation) -> dict:
    return {
        "id":         str(e.id),
        "from_level": e.from_level,
        "to_level":   e.to_level,
        "reason":     e.reason,
        "escalated_to_committee_id": str(e.escalated_to_committee_id) if e.escalated_to_committee_id else None,
        "escalated_by_user_id":      str(e.escalated_by_user_id)      if e.escalated_by_user_id      else None,
        "escalated_at": e.escalated_at.isoformat(),
    }


def resolution_out(r: FeedbackResolution) -> dict:
    return {
        "id":                 str(r.id),
        "resolution_summary": r.resolution_summary,
        "response_method":    r.response_method,
        "grievant_satisfied": r.grievant_satisfied,
        "grievant_response":  r.grievant_response,
        "appeal_filed":       r.appeal_filed,
        "witness_name":       r.witness_name,
        "resolved_by_user_id": str(r.resolved_by_user_id) if r.resolved_by_user_id else None,
        "resolved_at":        r.resolved_at.isoformat(),
    }


def appeal_out(a: FeedbackAppeal) -> dict:
    return {
        "id":              str(a.id),
        "appeal_grounds":  a.appeal_grounds,
        "appeal_outcome":  a.appeal_outcome,
        "appeal_status":   a.appeal_status,
        "court_referral_date": a.court_referral_date.isoformat() if a.court_referral_date else None,
        "filed_at":        a.filed_at.isoformat(),
        "reviewed_at":     a.reviewed_at.isoformat() if a.reviewed_at else None,
    }


def category_out(c: FeedbackCategoryDef) -> dict:
    return {
        "id":           str(c.id),
        "name":         c.name,
        "slug":         c.slug,
        "description":  c.description,
        "project_id":   str(c.project_id) if c.project_id else None,
        "applicable_types": (c.applicable_types or {}).get("types", []),
        "source":       c.source,
        "status":       c.status,
        "color_hex":    c.color_hex,
        "icon":         c.icon,
        "display_order": c.display_order,
        "ml_confidence":  c.ml_confidence,
        "ml_rationale":   c.ml_rationale,
        "merged_into_id": str(c.merged_into_id) if c.merged_into_id else None,
        "created_by_user_id":  str(c.created_by_user_id)  if c.created_by_user_id  else None,
        "reviewed_by_user_id": str(c.reviewed_by_user_id) if c.reviewed_by_user_id else None,
        "reviewed_at":   c.reviewed_at.isoformat() if c.reviewed_at else None,
        "review_notes":  c.review_notes,
        "created_at":    c.created_at.isoformat(),
    }


def committee_out(c: GrievanceCommittee) -> dict:
    return {
        "id":                 str(c.id),
        "name":               c.name,
        "level":              c.level,
        "project_id":         str(c.project_id)         if c.project_id         else None,
        "lga":                c.lga,
        "org_sub_project_id": str(c.org_sub_project_id) if c.org_sub_project_id else None,
        "stakeholder_ids":    c.get_stakeholder_ids(),
        "description":        c.description,
        "is_active":          c.is_active,
        "created_at":         c.created_at.isoformat(),
    }


def member_out(m: GrievanceCommitteeMember) -> dict:
    return {
        "id":           str(m.id),
        "committee_id": str(m.committee_id),
        "user_id":      str(m.user_id),
        "role":         m.role,
        "is_active":    m.is_active,
        "joined_at":    m.joined_at.isoformat(),
    }


def escalation_request_out(er: EscalationRequest) -> dict:
    return {
        "id":              str(er.id),
        "feedback_id":     str(er.feedback_id),
        "reason":          er.reason,
        "requested_level": er.requested_level,
        "status":          er.status.value,
        "reviewer_notes":  er.reviewer_notes,
        "requested_at":    er.requested_at.isoformat(),
        "reviewed_at":     er.reviewed_at.isoformat() if er.reviewed_at else None,
    }


def session_out(s: ChannelSession, include_turns: bool = False) -> dict:
    out = {
        "id":                  str(s.id),
        "channel":             s.channel.value,
        "status":              s.status.value,
        "language":            s.language,
        "project_id":          str(s.project_id)       if s.project_id       else None,
        "phone_number":        s.phone_number,
        "whatsapp_id":         s.whatsapp_id,
        "user_id":             str(s.user_id)           if s.user_id          else None,
        "stakeholder_id":      str(s.stakeholder_id)   if s.stakeholder_id   else None,
        "gateway_provider":    s.gateway_provider,
        "turn_count":          s.turn_count,
        "feedback_id":         str(s.feedback_id)      if s.feedback_id      else None,
        "extracted_data":      s.extracted_data,
        "is_officer_assisted": s.is_officer_assisted,
        "recorded_by_user_id": str(s.recorded_by_user_id) if s.recorded_by_user_id else None,
        "started_at":          s.started_at.isoformat(),
        "last_activity_at":    s.last_activity_at.isoformat(),
        "completed_at":        s.completed_at.isoformat() if s.completed_at else None,
        "end_reason":          s.end_reason,
    }
    if include_turns:
        out["turns"] = s.get_turns()
    return out
