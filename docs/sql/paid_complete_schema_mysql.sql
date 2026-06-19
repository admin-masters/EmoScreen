-- EmoScreen paid app complete schema fallback (MySQL)
-- Generated from Django migrations paid.0001_initial and paid.0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more.
-- Use only for a database where these paid/workflow tables do not already exist.
-- Prefer python manage.py migrate in normal deployment.

-- Migration: paid.0001_initial
--
-- Create model EsCfgForm
--
CREATE TABLE `es_cfg_forms` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `form_code` varchar(50) NOT NULL PRIMARY KEY, `title` varchar(255) NOT NULL, `age_min_months` integer UNSIGNED NOT NULL CHECK (`age_min_months` >= 0), `age_max_months` integer UNSIGNED NOT NULL CHECK (`age_max_months` >= 0), `language` varchar(8) NOT NULL, `version` varchar(64) NOT NULL, `is_active` bool NOT NULL, `symptom_question_count` integer UNSIGNED NOT NULL CHECK (`symptom_question_count` >= 0), `question_field_count` integer UNSIGNED NOT NULL CHECK (`question_field_count` >= 0), `total_score_max_php` numeric(8, 2) NULL, `total_score_max_computed` numeric(8, 2) NULL, `notes` longtext NOT NULL);
--
-- Create model EsCfgOptionSet
--
CREATE TABLE `es_cfg_option_sets` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `option_set_code` varchar(64) NOT NULL PRIMARY KEY, `name` varchar(255) NOT NULL, `widget` varchar(32) NOT NULL, `is_multi` bool NOT NULL, `notes` longtext NOT NULL);
--
-- Create model EsCfgEvaluationRule
--
CREATE TABLE `es_cfg_evaluation_rules` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `rule_code` varchar(64) NOT NULL PRIMARY KEY, `output_key` varchar(64) NOT NULL, `expression_jsonlogic` json NOT NULL, `notes` longtext NOT NULL, `form_code` varchar(50) NOT NULL);
--
-- Create model EsCfgOption
--
CREATE TABLE `es_cfg_options` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `option_code` varchar(64) NOT NULL PRIMARY KEY, `option_order` integer NOT NULL, `value` varchar(128) NOT NULL, `label` varchar(255) NOT NULL, `score_value` numeric(8, 2) NULL, `notes` longtext NOT NULL, `option_set_code` varchar(64) NOT NULL);
--
-- Create model EsCfgReportTemplate
--
CREATE TABLE `es_cfg_report_templates` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `template_code` varchar(64) NOT NULL PRIMARY KEY, `report_type` varchar(32) NOT NULL, `title` varchar(255) NOT NULL, `output_format` varchar(16) NOT NULL, `header_logo_path` varchar(255) NOT NULL, `footer_company` varchar(255) NOT NULL, `footer_tagline` varchar(255) NOT NULL, `footer_phone` varchar(64) NOT NULL, `footer_email` varchar(255) NOT NULL, `disclaimer_html` longtext NOT NULL, `notes` longtext NOT NULL, `form_code` varchar(50) NOT NULL);
--
-- Create model EsCfgReportBlock
--
CREATE TABLE `es_cfg_report_blocks` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `block_code` varchar(64) NOT NULL PRIMARY KEY, `block_order` integer NOT NULL, `block_type` varchar(64) NOT NULL, `title` varchar(255) NOT NULL, `text_template_html` longtext NOT NULL, `include_if_jsonlogic` json NULL, `params_json` json NULL, `notes` longtext NOT NULL, `template_code` varchar(64) NOT NULL);
--
-- Create model EsCfgScale
--
CREATE TABLE `es_cfg_scales` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `scale_code` varchar(64) NOT NULL PRIMARY KEY, `scale_key` varchar(64) NOT NULL, `label` varchar(255) NOT NULL, `calculation` varchar(32) NOT NULL, `max_score_override` numeric(8, 2) NULL, `group` varchar(64) NOT NULL, `notes` longtext NOT NULL, `max_score_computed` numeric(8, 2) NULL, `max_mismatch` bool NOT NULL, `max_mismatch_note` longtext NOT NULL, `form_code` varchar(50) NOT NULL);
--
-- Create model EsCfgSection
--
CREATE TABLE `es_cfg_sections` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `section_code` varchar(64) NOT NULL PRIMARY KEY, `section_key` varchar(64) NOT NULL, `title` varchar(255) NOT NULL, `instructions_html` longtext NOT NULL, `display_order` integer NOT NULL, `display_if_jsonlogic` json NULL, `notes` longtext NOT NULL, `form_code` varchar(50) NOT NULL);
--
-- Create model EsCfgQuestion
--
CREATE TABLE `es_cfg_questions` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `question_code` varchar(64) NOT NULL PRIMARY KEY, `question_key` varchar(64) NOT NULL, `question_order` integer NOT NULL, `global_order` integer NOT NULL, `legacy_field_name` varchar(128) NOT NULL, `question_text` longtext NOT NULL, `question_type` varchar(32) NOT NULL, `is_required` bool NOT NULL, `response_data_type` varchar(32) NOT NULL, `is_scored` bool NOT NULL, `store_target` varchar(64) NOT NULL, `validation_json` json NULL, `display_if_jsonlogic` json NULL, `notes` longtext NOT NULL, `form_code` varchar(50) NOT NULL, `option_set_code` varchar(64) NULL, `section_code` varchar(64) NOT NULL);
--
-- Create model EsCfgDerivedList
--
CREATE TABLE `es_cfg_derived_lists` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `list_code` varchar(64) NOT NULL PRIMARY KEY, `name` varchar(128) NOT NULL, `filter_response_value` varchar(255) NOT NULL, `notes` longtext NOT NULL, `form_code` varchar(50) NOT NULL, `section_code` varchar(64) NULL);
--
-- Create model EsCfgThreshold
--
CREATE TABLE `es_cfg_thresholds` (`created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `threshold_code` varchar(64) NOT NULL PRIMARY KEY, `basis` varchar(32) NOT NULL, `comparator` varchar(8) NOT NULL, `threshold_value` numeric(8, 3) NOT NULL, `risk_level` varchar(64) NOT NULL, `include_in_risk_table` bool NOT NULL, `include_in_patient_summary` bool NOT NULL, `priority` integer NOT NULL, `notes` longtext NOT NULL, `scale_code` varchar(64) NOT NULL);
--
-- Create model EsPayOrder
--
CREATE TABLE `es_pay_orders` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `order_code` varchar(32) NOT NULL UNIQUE, `price_variant` varchar(32) NOT NULL, `base_amount_paise` integer UNSIGNED NOT NULL CHECK (`base_amount_paise` >= 0), `discount_paise` integer UNSIGNED NOT NULL CHECK (`discount_paise` >= 0), `final_amount_paise` integer UNSIGNED NOT NULL CHECK (`final_amount_paise` >= 0), `patient_name` varchar(255) NOT NULL, `patient_whatsapp` varchar(32) NOT NULL, `patient_email` varchar(254) NULL, `status` varchar(32) NOT NULL, `link_token_hash` varchar(128) NOT NULL, `link_expires_at` datetime(6) NOT NULL, `paid_at` datetime(6) NULL, `submitted_at` datetime(6) NULL, `created_ip` char(39) NULL, `user_agent` longtext NOT NULL, `doctor_id` bigint NOT NULL, `form_code` varchar(50) NOT NULL);
--
-- Create model EsPayEmailLog
--
CREATE TABLE `es_pay_email_logs` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `email_type` varchar(32) NOT NULL, `to_email` varchar(254) NOT NULL, `subject` varchar(255) NOT NULL, `sendgrid_message_id` varchar(128) NOT NULL, `status` varchar(16) NOT NULL, `error_text` longtext NOT NULL, `created_at` datetime(6) NOT NULL, `order_id` bigint NULL);
--
-- Create model EsPayTransaction
--
CREATE TABLE `es_pay_transactions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `gateway` varchar(32) NOT NULL, `gateway_order_id` varchar(128) NOT NULL, `gateway_payment_id` varchar(128) NOT NULL, `gateway_signature` varchar(256) NOT NULL, `status` varchar(16) NOT NULL, `amount_paise` integer UNSIGNED NOT NULL CHECK (`amount_paise` >= 0), `currency` varchar(3) NOT NULL, `raw_payload_json` json NULL, `order_id` bigint NOT NULL);
--
-- Create model EsPayRevenueSplit
--
CREATE TABLE `es_pay_revenue_splits` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `party` varchar(16) NOT NULL, `percent` numeric(5, 2) NOT NULL, `amount_paise` integer UNSIGNED NOT NULL CHECK (`amount_paise` >= 0), `created_at` datetime(6) NOT NULL, `transaction_id` bigint NOT NULL);
--
-- Create model EsSubSubmission
--
CREATE TABLE `es_sub_submissions` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `config_version` varchar(64) NOT NULL, `child_name` varchar(255) NOT NULL, `child_dob` date NULL, `assessment_date` date NULL, `gender` varchar(16) NOT NULL, `completed_by` varchar(255) NOT NULL, `consent_given` bool NOT NULL, `status` varchar(16) NOT NULL, `total_score` numeric(8, 2) NULL, `total_score_max_display` numeric(8, 2) NULL, `has_concerns` bool NOT NULL, `computed_json` json NULL, `form_code` varchar(50) NOT NULL, `order_id` bigint NOT NULL UNIQUE);
--
-- Create model EsRepReport
--
CREATE TABLE `es_rep_reports` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `patient_pdf_path` varchar(500) NOT NULL, `doctor_pdf_path` varchar(500) NOT NULL, `patient_pdf_password_hint` varchar(255) NOT NULL, `doctor_pdf_password_hint` varchar(255) NOT NULL, `generated_at` datetime(6) NOT NULL, `emailed_to_parent_at` datetime(6) NULL, `emailed_to_doctor_at` datetime(6) NULL, `submission_id` bigint NOT NULL UNIQUE);
--
-- Create model EsCfgReportBlockScale
--
CREATE TABLE `es_cfg_report_block_scales` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `order` integer NOT NULL, `block_code` varchar(64) NOT NULL, `scale_code` varchar(64) NOT NULL);
--
-- Create model EsCfgScaleItem
--
CREATE TABLE `es_cfg_scale_items` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `weight` numeric(8, 2) NOT NULL, `item_order` integer NOT NULL, `notes` longtext NOT NULL, `question_code` varchar(64) NOT NULL, `scale_code` varchar(64) NOT NULL);
--
-- Create model EsCfgReportBlockSection
--
CREATE TABLE `es_cfg_report_block_sections` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `order` integer NOT NULL, `block_code` varchar(64) NOT NULL, `section_code` varchar(64) NOT NULL);
--
-- Create model EsSubScaleScore
--
CREATE TABLE `es_sub_scale_scores` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `score` numeric(8, 2) NOT NULL, `max_score` numeric(8, 2) NOT NULL, `risk_factor` numeric(8, 4) NOT NULL, `risk_percent` numeric(8, 2) NOT NULL, `included_in_doctor_table` bool NOT NULL, `created_at` datetime(6) NOT NULL, `scale_code` varchar(64) NOT NULL, `submission_id` bigint NOT NULL);
--
-- Create model EsSubAnswer
--
CREATE TABLE `es_sub_answers` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `value_json` json NOT NULL, `score_value` numeric(8, 2) NULL, `updated_at` datetime(6) NOT NULL, `question_code` varchar(64) NOT NULL, `submission_id` bigint NOT NULL);
ALTER TABLE `es_cfg_evaluation_rules` ADD CONSTRAINT `es_cfg_evaluation_ru_form_code_8002f6d4_fk_es_cfg_fo` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_cfg_options` ADD CONSTRAINT `es_cfg_options_option_set_code_d5f7ffc9_fk_es_cfg_op` FOREIGN KEY (`option_set_code`) REFERENCES `es_cfg_option_sets` (`option_set_code`);
ALTER TABLE `es_cfg_report_templates` ADD CONSTRAINT `es_cfg_report_templa_form_code_4d5c3c10_fk_es_cfg_fo` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_cfg_report_blocks` ADD CONSTRAINT `es_cfg_report_blocks_template_code_57ca068d_fk_es_cfg_re` FOREIGN KEY (`template_code`) REFERENCES `es_cfg_report_templates` (`template_code`);
ALTER TABLE `es_cfg_scales` ADD CONSTRAINT `es_cfg_scales_form_code_c3392673_fk_es_cfg_forms_form_code` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_cfg_sections` ADD CONSTRAINT `es_cfg_sections_form_code_594e92fa_fk_es_cfg_forms_form_code` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_cfg_questions` ADD CONSTRAINT `es_cfg_questions_form_code_2b0442a9_fk_es_cfg_forms_form_code` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_cfg_questions` ADD CONSTRAINT `es_cfg_questions_option_set_code_afc13d26_fk_es_cfg_op` FOREIGN KEY (`option_set_code`) REFERENCES `es_cfg_option_sets` (`option_set_code`);
ALTER TABLE `es_cfg_questions` ADD CONSTRAINT `es_cfg_questions_section_code_e82128d3_fk_es_cfg_se` FOREIGN KEY (`section_code`) REFERENCES `es_cfg_sections` (`section_code`);
ALTER TABLE `es_cfg_derived_lists` ADD CONSTRAINT `es_cfg_derived_lists_form_code_868c9baa_fk_es_cfg_fo` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_cfg_derived_lists` ADD CONSTRAINT `es_cfg_derived_lists_section_code_582eeb69_fk_es_cfg_se` FOREIGN KEY (`section_code`) REFERENCES `es_cfg_sections` (`section_code`);
ALTER TABLE `es_cfg_thresholds` ADD CONSTRAINT `es_cfg_thresholds_scale_code_036fd249_fk_es_cfg_sc` FOREIGN KEY (`scale_code`) REFERENCES `es_cfg_scales` (`scale_code`);
ALTER TABLE `es_pay_orders` ADD CONSTRAINT `es_pay_orders_doctor_id_442eccd0_fk_registered_professionals_id` FOREIGN KEY (`doctor_id`) REFERENCES `registered_professionals` (`id`);
ALTER TABLE `es_pay_orders` ADD CONSTRAINT `es_pay_orders_form_code_739271c0_fk_es_cfg_forms_form_code` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_pay_email_logs` ADD CONSTRAINT `es_pay_email_logs_order_id_b27e50d2_fk_es_pay_orders_id` FOREIGN KEY (`order_id`) REFERENCES `es_pay_orders` (`id`);
ALTER TABLE `es_pay_transactions` ADD CONSTRAINT `es_pay_transactions_order_id_c0f16f2c_fk_es_pay_orders_id` FOREIGN KEY (`order_id`) REFERENCES `es_pay_orders` (`id`);
ALTER TABLE `es_pay_revenue_splits` ADD CONSTRAINT `es_pay_revenue_split_transaction_id_50250697_fk_es_pay_tr` FOREIGN KEY (`transaction_id`) REFERENCES `es_pay_transactions` (`id`);
ALTER TABLE `es_sub_submissions` ADD CONSTRAINT `es_sub_submissions_form_code_c423f18d_fk_es_cfg_forms_form_code` FOREIGN KEY (`form_code`) REFERENCES `es_cfg_forms` (`form_code`);
ALTER TABLE `es_sub_submissions` ADD CONSTRAINT `es_sub_submissions_order_id_97fc6935_fk_es_pay_orders_id` FOREIGN KEY (`order_id`) REFERENCES `es_pay_orders` (`id`);
ALTER TABLE `es_rep_reports` ADD CONSTRAINT `es_rep_reports_submission_id_d0d56515_fk_es_sub_submissions_id` FOREIGN KEY (`submission_id`) REFERENCES `es_sub_submissions` (`id`);
ALTER TABLE `es_cfg_report_block_scales` ADD CONSTRAINT `es_cfg_report_block_scales_block_code_scale_code_03fc2185_uniq` UNIQUE (`block_code`, `scale_code`);
ALTER TABLE `es_cfg_report_block_scales` ADD CONSTRAINT `es_cfg_report_block__block_code_34cd7049_fk_es_cfg_re` FOREIGN KEY (`block_code`) REFERENCES `es_cfg_report_blocks` (`block_code`);
ALTER TABLE `es_cfg_report_block_scales` ADD CONSTRAINT `es_cfg_report_block__scale_code_5549b418_fk_es_cfg_sc` FOREIGN KEY (`scale_code`) REFERENCES `es_cfg_scales` (`scale_code`);
ALTER TABLE `es_cfg_scale_items` ADD CONSTRAINT `es_cfg_scale_items_scale_code_question_code_57eadea3_uniq` UNIQUE (`scale_code`, `question_code`);
ALTER TABLE `es_cfg_scale_items` ADD CONSTRAINT `es_cfg_scale_items_question_code_01c2c012_fk_es_cfg_qu` FOREIGN KEY (`question_code`) REFERENCES `es_cfg_questions` (`question_code`);
ALTER TABLE `es_cfg_scale_items` ADD CONSTRAINT `es_cfg_scale_items_scale_code_707d20b8_fk_es_cfg_sc` FOREIGN KEY (`scale_code`) REFERENCES `es_cfg_scales` (`scale_code`);
ALTER TABLE `es_cfg_report_block_sections` ADD CONSTRAINT `es_cfg_report_block_sect_block_code_section_code_59857f07_uniq` UNIQUE (`block_code`, `section_code`);
ALTER TABLE `es_cfg_report_block_sections` ADD CONSTRAINT `es_cfg_report_block__block_code_74d48f9b_fk_es_cfg_re` FOREIGN KEY (`block_code`) REFERENCES `es_cfg_report_blocks` (`block_code`);
ALTER TABLE `es_cfg_report_block_sections` ADD CONSTRAINT `es_cfg_report_block__section_code_7cc57db1_fk_es_cfg_se` FOREIGN KEY (`section_code`) REFERENCES `es_cfg_sections` (`section_code`);
ALTER TABLE `es_sub_scale_scores` ADD CONSTRAINT `es_sub_scale_scores_submission_id_scale_code_add9e235_uniq` UNIQUE (`submission_id`, `scale_code`);
ALTER TABLE `es_sub_scale_scores` ADD CONSTRAINT `es_sub_scale_scores_scale_code_146e5496_fk_es_cfg_sc` FOREIGN KEY (`scale_code`) REFERENCES `es_cfg_scales` (`scale_code`);
ALTER TABLE `es_sub_scale_scores` ADD CONSTRAINT `es_sub_scale_scores_submission_id_b8e0c12b_fk_es_sub_su` FOREIGN KEY (`submission_id`) REFERENCES `es_sub_submissions` (`id`);
ALTER TABLE `es_sub_answers` ADD CONSTRAINT `es_sub_answers_submission_id_question_code_5929a480_uniq` UNIQUE (`submission_id`, `question_code`);
ALTER TABLE `es_sub_answers` ADD CONSTRAINT `es_sub_answers_question_code_add7583f_fk_es_cfg_qu` FOREIGN KEY (`question_code`) REFERENCES `es_cfg_questions` (`question_code`);
ALTER TABLE `es_sub_answers` ADD CONSTRAINT `es_sub_answers_submission_id_5199b594_fk_es_sub_submissions_id` FOREIGN KEY (`submission_id`) REFERENCES `es_sub_submissions` (`id`);

-- Mark paid.0001_initial as applied after successful manual execution.

INSERT INTO django_migrations (app, name, applied)

SELECT 'paid', '0001_initial', NOW(6)

WHERE NOT EXISTS (

    SELECT 1 FROM django_migrations

    WHERE app = 'paid'

      AND name = '0001_initial'

);

-- Migration: paid.0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more
--
-- Create model WorkflowCase
--
CREATE TABLE `workflow_cases` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `case_code` varchar(32) NOT NULL UNIQUE, `doctor_name_snapshot` varchar(255) NOT NULL, `patient_name` varchar(255) NOT NULL, `patient_whatsapp` varchar(32) NOT NULL, `patient_email` varchar(254) NULL, `form_family` varchar(16) NOT NULL, `form_code` varchar(64) NOT NULL, `form_title` varchar(255) NOT NULL, `form_version` varchar(64) NOT NULL, `language` varchar(8) NOT NULL, `is_paid` bool NOT NULL, `amount_paise` integer UNSIGNED NOT NULL CHECK (`amount_paise` >= 0), `currency` varchar(3) NOT NULL, `payment_status` varchar(32) NOT NULL, `current_status` varchar(32) NOT NULL, `completion_percent` numeric(5, 2) NOT NULL, `completed_questions` integer UNSIGNED NOT NULL CHECK (`completed_questions` >= 0), `total_questions` integer UNSIGNED NOT NULL CHECK (`total_questions` >= 0), `access_token_hash` varchar(128) NOT NULL, `source` varchar(64) NOT NULL, `created_by_user_email` varchar(254) NULL, `created_ip` char(39) NULL, `user_agent` longtext NOT NULL, `sent_at` datetime(6) NULL, `delivered_at` datetime(6) NULL, `opened_at` datetime(6) NULL, `in_progress_at` datetime(6) NULL, `payment_completed_at` datetime(6) NULL, `submitted_at` datetime(6) NULL, `report_generated_at` datetime(6) NULL, `report_sent_at` datetime(6) NULL, `completed_at` datetime(6) NULL, `failed_at` datetime(6) NULL, `failure_stage` varchar(64) NOT NULL, `failure_reason` longtext NOT NULL, `last_event_at` datetime(6) NULL, `metadata_json` json NULL, `doctor_id` bigint NOT NULL, `legacy_submission_id` bigint NULL UNIQUE, `order_id` bigint NULL UNIQUE, `paid_submission_id` bigint NULL UNIQUE, `report_id` bigint NULL UNIQUE);
--
-- Create model WorkflowDeliveryAttempt
--
CREATE TABLE `workflow_delivery_attempts` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `channel` varchar(16) NOT NULL, `recipient` varchar(255) NOT NULL, `subject` varchar(255) NOT NULL, `status` varchar(16) NOT NULL, `provider` varchar(64) NOT NULL, `provider_message_id` varchar(128) NOT NULL, `sent_at` datetime(6) NULL, `delivered_at` datetime(6) NULL, `opened_at` datetime(6) NULL, `error_text` longtext NOT NULL, `metadata_json` json NULL, `created_at` datetime(6) NOT NULL, `case_id` bigint NOT NULL, `email_log_id` bigint NULL);
--
-- Create model WorkflowEvent
--
CREATE TABLE `workflow_events` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `event_type` varchar(64) NOT NULL, `stage` varchar(64) NOT NULL, `status_from` varchar(32) NOT NULL, `status_to` varchar(32) NOT NULL, `actor_type` varchar(16) NOT NULL, `actor_identifier` varchar(255) NOT NULL, `message` longtext NOT NULL, `failure_reason` longtext NOT NULL, `metadata_json` json NULL, `occurred_at` datetime(6) NOT NULL, `case_id` bigint NOT NULL);
--
-- Create model WorkflowPayment
--
CREATE TABLE `workflow_payments` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `is_required` bool NOT NULL, `amount_paise` integer UNSIGNED NOT NULL CHECK (`amount_paise` >= 0), `currency` varchar(3) NOT NULL, `gateway` varchar(32) NOT NULL, `status` varchar(32) NOT NULL, `reference_id` varchar(128) NOT NULL, `paid_at` datetime(6) NULL, `failed_at` datetime(6) NULL, `refunded_at` datetime(6) NULL, `error_text` longtext NOT NULL, `raw_payload_json` json NULL, `case_id` bigint NOT NULL UNIQUE, `order_id` bigint NULL, `transaction_id` bigint NULL);
--
-- Create model WorkflowReport
--
CREATE TABLE `workflow_reports` (`id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, `created_at` datetime(6) NOT NULL, `updated_at` datetime(6) NOT NULL, `status` varchar(32) NOT NULL, `generation_started_at` datetime(6) NULL, `generated_at` datetime(6) NULL, `sent_to_doctor_at` datetime(6) NULL, `sent_to_patient_at` datetime(6) NULL, `doctor_delivery_status` varchar(32) NOT NULL, `patient_delivery_status` varchar(32) NOT NULL, `error_text` longtext NOT NULL, `metadata_json` json NULL, `case_id` bigint NOT NULL UNIQUE, `legacy_submission_id` bigint NULL, `paid_submission_id` bigint NULL, `report_id` bigint NULL);
--
-- Create index workflow_ca_doctor__e68dca_idx on field(s) doctor, current_status of model workflowcase
--
CREATE INDEX `workflow_ca_doctor__e68dca_idx` ON `workflow_cases` (`doctor_id`, `current_status`);
--
-- Create index workflow_ca_form_fa_0c6c8b_idx on field(s) form_family, current_status of model workflowcase
--
CREATE INDEX `workflow_ca_form_fa_0c6c8b_idx` ON `workflow_cases` (`form_family`, `current_status`);
--
-- Create index workflow_ca_payment_f95a05_idx on field(s) payment_status of model workflowcase
--
CREATE INDEX `workflow_ca_payment_f95a05_idx` ON `workflow_cases` (`payment_status`);
--
-- Create index workflow_ca_created_ba6786_idx on field(s) created_at of model workflowcase
--
CREATE INDEX `workflow_ca_created_ba6786_idx` ON `workflow_cases` (`created_at`);
--
-- Create index workflow_de_case_id_2428dd_idx on field(s) case, channel of model workflowdeliveryattempt
--
CREATE INDEX `workflow_de_case_id_2428dd_idx` ON `workflow_delivery_attempts` (`case_id`, `channel`);
--
-- Create index workflow_de_status_53f785_idx on field(s) status of model workflowdeliveryattempt
--
CREATE INDEX `workflow_de_status_53f785_idx` ON `workflow_delivery_attempts` (`status`);
--
-- Create index workflow_de_created_49ebe1_idx on field(s) created_at of model workflowdeliveryattempt
--
CREATE INDEX `workflow_de_created_49ebe1_idx` ON `workflow_delivery_attempts` (`created_at`);
--
-- Create index workflow_ev_case_id_6f8739_idx on field(s) case, occurred_at of model workflowevent
--
CREATE INDEX `workflow_ev_case_id_6f8739_idx` ON `workflow_events` (`case_id`, `occurred_at`);
--
-- Create index workflow_ev_event_t_e83845_idx on field(s) event_type of model workflowevent
--
CREATE INDEX `workflow_ev_event_t_e83845_idx` ON `workflow_events` (`event_type`);
--
-- Create index workflow_ev_stage_972095_idx on field(s) stage of model workflowevent
--
CREATE INDEX `workflow_ev_stage_972095_idx` ON `workflow_events` (`stage`);
--
-- Create index workflow_pa_status_127554_idx on field(s) status of model workflowpayment
--
CREATE INDEX `workflow_pa_status_127554_idx` ON `workflow_payments` (`status`);
--
-- Create index workflow_pa_gateway_260d6e_idx on field(s) gateway of model workflowpayment
--
CREATE INDEX `workflow_pa_gateway_260d6e_idx` ON `workflow_payments` (`gateway`);
--
-- Create index workflow_re_status_d344a2_idx on field(s) status of model workflowreport
--
CREATE INDEX `workflow_re_status_d344a2_idx` ON `workflow_reports` (`status`);
--
-- Create index workflow_re_generat_d71c29_idx on field(s) generated_at of model workflowreport
--
CREATE INDEX `workflow_re_generat_d71c29_idx` ON `workflow_reports` (`generated_at`);
ALTER TABLE `workflow_cases` ADD CONSTRAINT `workflow_cases_doctor_id_8aadb682_fk_registered_professionals_id` FOREIGN KEY (`doctor_id`) REFERENCES `registered_professionals` (`id`);
ALTER TABLE `workflow_cases` ADD CONSTRAINT `workflow_cases_legacy_submission_id_6c0479ff_fk_submissions_id` FOREIGN KEY (`legacy_submission_id`) REFERENCES `submissions` (`id`);
ALTER TABLE `workflow_cases` ADD CONSTRAINT `workflow_cases_order_id_0f381bbc_fk_es_pay_orders_id` FOREIGN KEY (`order_id`) REFERENCES `es_pay_orders` (`id`);
ALTER TABLE `workflow_cases` ADD CONSTRAINT `workflow_cases_paid_submission_id_786222b2_fk_es_sub_su` FOREIGN KEY (`paid_submission_id`) REFERENCES `es_sub_submissions` (`id`);
ALTER TABLE `workflow_cases` ADD CONSTRAINT `workflow_cases_report_id_9ad89a1e_fk_es_rep_reports_id` FOREIGN KEY (`report_id`) REFERENCES `es_rep_reports` (`id`);
CREATE INDEX `workflow_cases_access_token_hash_b134a02a` ON `workflow_cases` (`access_token_hash`);
ALTER TABLE `workflow_delivery_attempts` ADD CONSTRAINT `workflow_delivery_attempts_case_id_54df2080_fk_workflow_cases_id` FOREIGN KEY (`case_id`) REFERENCES `workflow_cases` (`id`);
ALTER TABLE `workflow_delivery_attempts` ADD CONSTRAINT `workflow_delivery_at_email_log_id_c3f05f17_fk_es_pay_em` FOREIGN KEY (`email_log_id`) REFERENCES `es_pay_email_logs` (`id`);
ALTER TABLE `workflow_events` ADD CONSTRAINT `workflow_events_case_id_734a49ca_fk_workflow_cases_id` FOREIGN KEY (`case_id`) REFERENCES `workflow_cases` (`id`);
ALTER TABLE `workflow_payments` ADD CONSTRAINT `workflow_payments_case_id_008d0b3d_fk_workflow_cases_id` FOREIGN KEY (`case_id`) REFERENCES `workflow_cases` (`id`);
ALTER TABLE `workflow_payments` ADD CONSTRAINT `workflow_payments_order_id_e429fdec_fk_es_pay_orders_id` FOREIGN KEY (`order_id`) REFERENCES `es_pay_orders` (`id`);
ALTER TABLE `workflow_payments` ADD CONSTRAINT `workflow_payments_transaction_id_9f94cd2f_fk_es_pay_tr` FOREIGN KEY (`transaction_id`) REFERENCES `es_pay_transactions` (`id`);
ALTER TABLE `workflow_reports` ADD CONSTRAINT `workflow_reports_case_id_6fba3239_fk_workflow_cases_id` FOREIGN KEY (`case_id`) REFERENCES `workflow_cases` (`id`);
ALTER TABLE `workflow_reports` ADD CONSTRAINT `workflow_reports_legacy_submission_id_38eed6aa_fk_submissions_id` FOREIGN KEY (`legacy_submission_id`) REFERENCES `submissions` (`id`);
ALTER TABLE `workflow_reports` ADD CONSTRAINT `workflow_reports_paid_submission_id_e85d9c92_fk_es_sub_su` FOREIGN KEY (`paid_submission_id`) REFERENCES `es_sub_submissions` (`id`);
ALTER TABLE `workflow_reports` ADD CONSTRAINT `workflow_reports_report_id_92f4d935_fk_es_rep_reports_id` FOREIGN KEY (`report_id`) REFERENCES `es_rep_reports` (`id`);

-- Mark paid.0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more as applied after successful manual execution.

INSERT INTO django_migrations (app, name, applied)

SELECT 'paid', '0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more', NOW(6)

WHERE NOT EXISTS (

    SELECT 1 FROM django_migrations

    WHERE app = 'paid'

      AND name = '0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more'

);
