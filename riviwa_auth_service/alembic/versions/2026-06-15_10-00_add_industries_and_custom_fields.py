"""Add Industry M2M, OrgCustomFieldDefinition, custom_fields JSONB columns

Revision ID: d1e2f3a4b5c6
Revises: b7c8d9e0f1a2
Create Date: 2026-06-15 10:00:00.000000
"""
from __future__ import annotations
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from alembic import op

revision = "d1e2f3a4b5c6"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── industries ────────────────────────────────────────────────────────────
    op.create_table(
        "industries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_url", sa.String(512), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["parent_id"], ["industries.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_industries_slug", "industries", ["slug"])
    op.create_index("ix_industries_is_active", "industries", ["is_active"])

    # ── organisation_industries (M2M) ─────────────────────────────────────────
    op.create_table(
        "organisation_industries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("industry_id", sa.UUID(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["industry_id"], ["industries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "industry_id", name="uq_org_industry"),
    )
    op.create_index("ix_organisation_industries_org_id", "organisation_industries", ["org_id"])
    op.create_index("ix_organisation_industries_industry_id", "organisation_industries", ["industry_id"])

    # ── org_custom_field_defs ─────────────────────────────────────────────────
    op.create_table(
        "org_custom_field_defs",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("label_sw", sa.String(200), nullable=True),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options", JSONB(), nullable=True),
        sa.Column("placeholder", sa.String(300), nullable=True),
        sa.Column("help_text", sa.String(500), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default="false"),
        sa.Column("is_visible_to_consumer", sa.Boolean(), server_default="true"),
        sa.Column("feedback_types", JSONB(), nullable=True),
        sa.Column("industry_template_key", sa.String(80), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_by_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "entity_type", "field_key", name="uq_org_entity_field_key"),
    )
    op.create_index("ix_org_custom_field_defs_org_id", "org_custom_field_defs", ["org_id"])
    op.create_index("ix_org_custom_field_defs_entity_type", "org_custom_field_defs", ["entity_type"])

    # ── industry_field_templates ──────────────────────────────────────────────
    op.create_table(
        "industry_field_templates",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("industry_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("label_sw", sa.String(200), nullable=True),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options", JSONB(), nullable=True),
        sa.Column("placeholder", sa.String(300), nullable=True),
        sa.Column("help_text", sa.String(500), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default="false"),
        sa.Column("is_visible_to_consumer", sa.Boolean(), server_default="true"),
        sa.Column("feedback_types", JSONB(), nullable=True),
        sa.Column("source_standard", sa.String(200), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.ForeignKeyConstraint(["industry_id"], ["industries.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("industry_id", "entity_type", "field_key", name="uq_industry_entity_field"),
    )
    op.create_index("ix_industry_field_templates_industry_id", "industry_field_templates", ["industry_id"])

    # ── custom_fields JSONB on existing tables ────────────────────────────────
    op.add_column("organisations", sa.Column("custom_fields", JSONB(), nullable=True))
    op.add_column("org_branches", sa.Column("custom_fields", JSONB(), nullable=True))
    op.add_column("org_departments", sa.Column("custom_fields", JSONB(), nullable=True))
    op.add_column("org_services", sa.Column("custom_fields", JSONB(), nullable=True))

    # ── Seed 33 industries ────────────────────────────────────────────────────
    op.execute("""
    INSERT INTO industries (id, name, slug, sort_order, is_active, created_at, updated_at) VALUES
      (gen_random_uuid(), 'Healthcare / Hospital',            'healthcare',              1,  true, now(), now()),
      (gen_random_uuid(), 'Pharmacy / Pharmaceutical',        'pharmacy',                2,  true, now(), now()),
      (gen_random_uuid(), 'Finance / Banking',                'finance-banking',         3,  true, now(), now()),
      (gen_random_uuid(), 'Insurance',                        'insurance',               4,  true, now(), now()),
      (gen_random_uuid(), 'Telecommunications',               'telecommunications',      5,  true, now(), now()),
      (gen_random_uuid(), 'Energy / Utilities / Water',       'energy-utilities',        6,  true, now(), now()),
      (gen_random_uuid(), 'Government / Public Services',     'government-services',     7,  true, now(), now()),
      (gen_random_uuid(), 'Embassy / Immigration',            'embassy-immigration',     8,  true, now(), now()),
      (gen_random_uuid(), 'NGO / Development',                'ngo-development',         9,  true, now(), now()),
      (gen_random_uuid(), 'Retail / Consumer Products',       'retail',                  10, true, now(), now()),
      (gen_random_uuid(), 'Food & Consumables',               'food-consumables',        11, true, now(), now()),
      (gen_random_uuid(), 'Electronics & Technology',         'electronics',             12, true, now(), now()),
      (gen_random_uuid(), 'Transport / Public Transit',       'transport',               13, true, now(), now()),
      (gen_random_uuid(), 'Logistics / Supply Chain',         'logistics',               14, true, now(), now()),
      (gen_random_uuid(), 'Automobiles / Motor Vehicles',     'automobiles',             15, true, now(), now()),
      (gen_random_uuid(), 'Education / University',           'education',               16, true, now(), now()),
      (gen_random_uuid(), 'Training / Professional Dev',      'training',                17, true, now(), now()),
      (gen_random_uuid(), 'Business Consultancy',             'consultancy',             18, true, now(), now()),
      (gen_random_uuid(), 'Legal Services',                   'legal',                   19, true, now(), now()),
      (gen_random_uuid(), 'Construction / Real Estate Dev',   'construction',            20, true, now(), now()),
      (gen_random_uuid(), 'Real Estate / Property',           'real-estate',             21, true, now(), now()),
      (gen_random_uuid(), 'Mining / Extractive Industries',   'mining',                  22, true, now(), now()),
      (gen_random_uuid(), 'Social Welfare',                   'social-welfare',          23, true, now(), now()),
      (gen_random_uuid(), 'Tourism / Hospitality',            'tourism',                 24, true, now(), now()),
      (gen_random_uuid(), 'Agriculture / Agribusiness',       'agriculture',             25, true, now(), now()),
      (gen_random_uuid(), 'Events / Entertainment',           'events',                  26, true, now(), now()),
      (gen_random_uuid(), 'Church / Religious Organizations', 'religious',               27, true, now(), now()),
      (gen_random_uuid(), 'Media / Entertainment',            'media',                   28, true, now(), now()),
      (gen_random_uuid(), 'Personal Development / Coaching',  'personal-development',    29, true, now(), now()),
      (gen_random_uuid(), 'Technology / Software',            'technology-software',     30, true, now(), now()),
      (gen_random_uuid(), 'Manufacturing',                    'manufacturing',           31, true, now(), now()),
      (gen_random_uuid(), 'Security Services',                'security',                32, true, now(), now()),
      (gen_random_uuid(), 'Health & Wellness',                'health-wellness',         33, true, now(), now())
    ON CONFLICT (slug) DO NOTHING;
    """)

    # ── Seed healthcare field templates ──────────────────────────────────────
    op.execute("""
    INSERT INTO industry_field_templates
      (id, industry_id, entity_type, field_key, label, label_sw, field_type, is_required, is_visible_to_consumer, feedback_types, source_standard, sort_order)
    SELECT
      gen_random_uuid(),
      i.id,
      t.entity_type,
      t.field_key,
      t.label,
      t.label_sw,
      t.field_type,
      t.is_required,
      t.is_visible_to_consumer,
      t.feedback_types::jsonb,
      t.source_standard,
      t.sort_order
    FROM industries i
    CROSS JOIN (VALUES
      ('feedback','patient_file_number','Patient File / Hospital Number','Nambari ya Faili la Mgonjwa','text',true,true,'["grievance","inquiry"]','WHO ICPS; MOHCDGEC Patient Charter 2019',1),
      ('feedback','nhif_membership_number','NHIF Membership Number','Nambari ya NHIF','text',false,false,'["grievance"]','NHIF Act Cap.395',2),
      ('feedback','treating_clinician_name','Treating Clinician Name','Jina la Daktari / Muuguzi','text',false,true,'["grievance"]','WHO ICPS; JCI PCC.3.1',3),
      ('feedback','department_or_ward','Department / Ward','Idara / Wodi','text',true,true,'["grievance","suggestion","inquiry"]','MOHCDGEC; NRLS',4),
      ('feedback','stage_of_care','Stage of Care','Hatua ya Matibabu','select',false,true,'["grievance"]','HCAT 7-category framework',5),
      ('feedback','harm_level','Patient Harm Level','Kiwango cha Madhara kwa Mgonjwa','select',false,false,'["grievance"]','NHS NRLS 5-level scale',6),
      ('feedback','consent_to_share_with_clinician','Consent to Share with Clinician','Ridhaa ya Kushiriki na Daktari','boolean',true,false,'["grievance"]','JCI PCC.3.1; GDPR',7),
      ('feedback','date_of_admission','Date of Admission','Tarehe ya Kulazwa','date',false,true,'["grievance"]','ISO 10002:2018',8)
    ) AS t(entity_type,field_key,label,label_sw,field_type,is_required,is_visible_to_consumer,feedback_types,source_standard,sort_order)
    WHERE i.slug = 'healthcare'
    ON CONFLICT (industry_id, entity_type, field_key) DO NOTHING;
    """)

    # ── Seed pharmacy field templates ─────────────────────────────────────────
    op.execute("""
    INSERT INTO industry_field_templates
      (id, industry_id, entity_type, field_key, label, label_sw, field_type, is_required, is_visible_to_consumer, feedback_types, source_standard, sort_order)
    SELECT
      gen_random_uuid(), i.id, t.entity_type, t.field_key, t.label, t.label_sw,
      t.field_type, t.is_required, t.is_visible_to_consumer,
      t.feedback_types::jsonb, t.source_standard, t.sort_order
    FROM industries i
    CROSS JOIN (VALUES
      ('feedback','drug_name_generic','Drug Name (Generic)','Jina la Dawa (la Kawaida)','text',true,true,'["grievance"]','WHO pharmacovigilance; TMDA Yellow Form',1),
      ('feedback','drug_batch_lot_number','Batch / Lot Number','Nambari ya Kundi la Dawa','text',false,true,'["grievance"]','TMDA; FDA MedWatch ADR',2),
      ('feedback','drug_manufacturer','Drug Manufacturer','Mtengenezaji wa Dawa','text',false,true,'["grievance"]','TMDA; WHO pharmacovigilance',3),
      ('feedback','drug_expiry_date','Drug Expiry Date','Tarehe ya Muda wa Dawa','date',false,true,'["grievance"]','TMDA; WHO',4),
      ('feedback','adverse_effect_description','Adverse Effect Experienced','Athari Mbaya Iliyotokea','textarea',false,true,'["grievance"]','WHO CIOMS; TMDA VigiFlow',5),
      ('feedback','time_to_onset_hours','Time from Administration to Effect (hours)','Muda kutoka Dawa hadi Athari (masaa)','number',false,false,'["grievance"]','WHO pharmacovigilance',6),
      ('feedback','prescriber_name','Prescribing Clinician Name','Jina la Daktari Aliyeandika Dawa','text',false,true,'["grievance"]','TMDA; WHO CIOMS',7),
      ('feedback','other_medications_taken','Other Medications Taken','Dawa Nyingine Zinazotumiwa','textarea',false,false,'["grievance"]','WHO pharmacovigilance drug interactions',8),
      ('feedback','tmda_reported','Reported to TMDA?','Je, TMDA Waliarifu?','boolean',false,false,'["grievance"]','TMDA Act; pharmacovigilance',9)
    ) AS t(entity_type,field_key,label,label_sw,field_type,is_required,is_visible_to_consumer,feedback_types,source_standard,sort_order)
    WHERE i.slug = 'pharmacy'
    ON CONFLICT (industry_id, entity_type, field_key) DO NOTHING;
    """)

    # ── Seed banking field templates ──────────────────────────────────────────
    op.execute("""
    INSERT INTO industry_field_templates
      (id, industry_id, entity_type, field_key, label, label_sw, field_type, is_required, is_visible_to_consumer, feedback_types, source_standard, sort_order)
    SELECT gen_random_uuid(), i.id, t.entity_type, t.field_key, t.label, t.label_sw,
      t.field_type, t.is_required, t.is_visible_to_consumer,
      t.feedback_types::jsonb, t.source_standard, t.sort_order
    FROM industries i
    CROSS JOIN (VALUES
      ('feedback','account_type','Account Type','Aina ya Akaunti','select',false,true,'["grievance","inquiry"]','FCA DISP; BoT consumer framework',1),
      ('feedback','transaction_reference','Transaction Reference No.','Nambari ya Rejea ya Muamala','text',false,true,'["grievance"]','FCA DISP; BoT',2),
      ('feedback','transaction_date','Transaction Date','Tarehe ya Muamala','date',false,true,'["grievance"]','FCA DISP',3),
      ('feedback','amount_disputed_tzs','Amount Disputed (TZS)','Kiasi Kinachogombaniwa (TZS)','currency',false,true,'["grievance"]','FCA DISP; BoT',4),
      ('feedback','fraud_suspected','Fraud Suspected?','Je, Udhanganyifu Unashukiwa?','boolean',false,false,'["grievance"]','FCA DISP; AML/KYC framework',5),
      ('feedback','police_report_number','Police Report Number (if fraud)','Nambari ya Ripoti ya Polisi','text',false,false,'["grievance"]','BoT fraud reporting',6),
      ('feedback','channel_used','Channel of Transaction','Njia ya Muamala','select',false,true,'["grievance"]','BoT consumer protection',7),
      ('feedback','previous_complaint_ref_to_bank','Previous Complaint Reference to Bank','Rejea ya Malalamiko ya Awali kwa Benki','text',false,false,'["grievance"]','FCA DISP Reg 9',8)
    ) AS t(entity_type,field_key,label,label_sw,field_type,is_required,is_visible_to_consumer,feedback_types,source_standard,sort_order)
    WHERE i.slug = 'finance-banking'
    ON CONFLICT (industry_id, entity_type, field_key) DO NOTHING;
    """)

    # ── Seed mining field templates ───────────────────────────────────────────
    op.execute("""
    INSERT INTO industry_field_templates
      (id, industry_id, entity_type, field_key, label, label_sw, field_type, is_required, is_visible_to_consumer, feedback_types, source_standard, sort_order)
    SELECT gen_random_uuid(), i.id, t.entity_type, t.field_key, t.label, t.label_sw,
      t.field_type, t.is_required, t.is_visible_to_consumer,
      t.feedback_types::jsonb, t.source_standard, t.sort_order
    FROM industries i
    CROSS JOIN (VALUES
      ('feedback','mine_company_name','Mine / Company Name','Jina la Mgodi / Kampuni','text',true,true,'["grievance","inquiry"]','ICMM 2019; IFC GPN 2009',1),
      ('feedback','mining_licence_number','Mining Licence Number','Nambari ya Leseni ya Uchimbaji','text',false,true,'["grievance"]','Tanzania Mining Act 2010 s.97',2),
      ('feedback','land_area_affected_hectares','Land Area Affected (hectares)','Eneo Lililoharibiwa (hekta)','decimal',false,true,'["grievance"]','IFC PS5; Tanzania Mining Act s.97',3),
      ('feedback','households_affected_count','Number of Households Affected','Idadi ya Kaya Zilizoathirika','number',false,true,'["grievance"]','World Bank ESS10; ICMM 2019',4),
      ('feedback','pollution_type','Type of Pollution','Aina ya Uchafuzi','select',false,true,'["grievance"]','NEMC; IFC PS4; ICMM 2019',5),
      ('feedback','nemc_reference_number','NEMC Reference Number','Nambari ya Kesi ya NEMC','text',false,false,'["grievance"]','Tanzania Environmental Management Act Cap.191',6),
      ('feedback','compensation_reference','Compensation Reference No.','Nambari ya Fidia','text',false,false,'["grievance"]','IFC PS5; Tanzania Mining Act',7),
      ('feedback','complainant_type','Complainant Type','Aina ya Mlalamikaji','select',false,false,'["grievance"]','ICMM 2019 GRM Principles',8),
      ('feedback','vulnerability_status','Vulnerability Status','Hali ya Udhaifu','select',false,false,'["grievance"]','IFC PS7; World Bank ESS10',9)
    ) AS t(entity_type,field_key,label,label_sw,field_type,is_required,is_visible_to_consumer,feedback_types,source_standard,sort_order)
    WHERE i.slug = 'mining'
    ON CONFLICT (industry_id, entity_type, field_key) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_column("org_services", "custom_fields")
    op.drop_column("org_departments", "custom_fields")
    op.drop_column("org_branches", "custom_fields")
    op.drop_column("organisations", "custom_fields")
    op.drop_index("ix_industry_field_templates_industry_id", table_name="industry_field_templates")
    op.drop_table("industry_field_templates")
    op.drop_index("ix_org_custom_field_defs_entity_type", table_name="org_custom_field_defs")
    op.drop_index("ix_org_custom_field_defs_org_id", table_name="org_custom_field_defs")
    op.drop_table("org_custom_field_defs")
    op.drop_index("ix_organisation_industries_industry_id", table_name="organisation_industries")
    op.drop_index("ix_organisation_industries_org_id", table_name="organisation_industries")
    op.drop_table("organisation_industries")
    op.drop_index("ix_industries_is_active", table_name="industries")
    op.drop_index("ix_industries_slug", table_name="industries")
    op.drop_table("industries")
