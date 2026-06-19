from django.contrib import admin

from . import models


admin.site.register(models.EsCfgForm)
admin.site.register(models.EsCfgSection)
admin.site.register(models.EsCfgOptionSet)
admin.site.register(models.EsCfgOption)
admin.site.register(models.EsCfgQuestion)
admin.site.register(models.EsCfgScale)
admin.site.register(models.EsCfgScaleItem)
admin.site.register(models.EsCfgThreshold)
admin.site.register(models.EsCfgDerivedList)
admin.site.register(models.EsCfgEvaluationRule)
admin.site.register(models.EsCfgReportTemplate)
admin.site.register(models.EsCfgReportBlock)
admin.site.register(models.EsCfgReportBlockSection)
admin.site.register(models.EsCfgReportBlockScale)
admin.site.register(models.EsPayOrder)
admin.site.register(models.EsPayTransaction)
admin.site.register(models.EsPayRevenueSplit)
admin.site.register(models.EsPayEmailLog)
admin.site.register(models.EsSubSubmission)
admin.site.register(models.EsSubAnswer)
admin.site.register(models.EsSubScaleScore)
admin.site.register(models.EsRepReport)


@admin.register(models.WorkflowCase)
class WorkflowCaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_code",
        "doctor_name_snapshot",
        "patient_name",
        "form_family",
        "current_status",
        "payment_status",
        "completion_percent",
        "created_at",
        "last_event_at",
    )
    list_filter = ("form_family", "current_status", "payment_status", "is_paid", "created_at")
    search_fields = (
        "case_code",
        "doctor_name_snapshot",
        "patient_name",
        "patient_whatsapp",
        "patient_email",
        "order__order_code",
        "doctor__unique_doctor_code",
    )
    readonly_fields = ("case_code", "created_at", "updated_at", "last_event_at")


@admin.register(models.WorkflowEvent)
class WorkflowEventAdmin(admin.ModelAdmin):
    list_display = ("case", "event_type", "stage", "status_from", "status_to", "actor_type", "occurred_at")
    list_filter = ("event_type", "stage", "actor_type", "occurred_at")
    search_fields = ("case__case_code", "event_type", "message", "failure_reason", "actor_identifier")
    readonly_fields = (
        "case",
        "event_type",
        "stage",
        "status_from",
        "status_to",
        "actor_type",
        "actor_identifier",
        "message",
        "failure_reason",
        "metadata_json",
        "occurred_at",
    )


@admin.register(models.WorkflowDeliveryAttempt)
class WorkflowDeliveryAttemptAdmin(admin.ModelAdmin):
    list_display = ("case", "channel", "recipient", "status", "provider", "created_at")
    list_filter = ("channel", "status", "provider", "created_at")
    search_fields = ("case__case_code", "recipient", "provider_message_id", "error_text")


@admin.register(models.WorkflowPayment)
class WorkflowPaymentAdmin(admin.ModelAdmin):
    list_display = ("case", "status", "gateway", "amount_paise", "reference_id", "paid_at", "failed_at")
    list_filter = ("status", "gateway", "is_required", "paid_at", "failed_at")
    search_fields = ("case__case_code", "order__order_code", "reference_id")


@admin.register(models.WorkflowReport)
class WorkflowReportAdmin(admin.ModelAdmin):
    list_display = ("case", "status", "generated_at", "sent_to_doctor_at", "sent_to_patient_at")
    list_filter = ("status", "generated_at", "sent_to_doctor_at", "sent_to_patient_at")
    search_fields = ("case__case_code", "doctor_delivery_status", "patient_delivery_status", "error_text")
