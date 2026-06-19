-- EmoScreen paid workflow/audit migration fallback (MySQL)
-- Generated from Django migration: paid.0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more
-- Use only if python manage.py migrate paid 0002 cannot be run successfully.
-- Assumes paid.0001_initial has already been applied and base content tables exist.

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

-- Mark migration as applied after successful manual execution.

INSERT INTO django_migrations (app, name, applied)

SELECT 'paid', '0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more', NOW(6)

WHERE NOT EXISTS (

    SELECT 1 FROM django_migrations

    WHERE app = 'paid'

      AND name = '0002_workflowcase_workflowdeliveryattempt_workflowevent_and_more'

);
