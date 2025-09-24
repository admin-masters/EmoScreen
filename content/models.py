# content/models.py
from django.db import models

class Language(models.Model):
    lang_code = models.CharField(primary_key=True, max_length=8)
    lang_name_english = models.CharField(max_length=64)
    lang_name_native = models.CharField(max_length=64)

    class Meta:
        db_table = "languages"

class RegisteredProfessional(models.Model):
    class Role(models.TextChoices):
        PEDIATRICIAN = "PEDIATRICIAN"
        CAREGIVER = "CAREGIVER"

    role = models.CharField(max_length=20, choices=Role.choices)
    salutation = models.CharField(max_length=16, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(unique=True, max_length=191)
    whatsapp = models.CharField(max_length=32, null=True, blank=True)
    imc_registration_number = models.CharField(max_length=64, null=True, blank=True)
    appointment_booking_number = models.CharField(max_length=64, null=True, blank=True)
    clinic_address = models.TextField(null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    state = models.CharField(max_length=64, null=True, blank=True)
    district = models.CharField(max_length=64, null=True, blank=True)
    receptionist_whatsapp = models.CharField(max_length=32, null=True, blank=True)
    photo_url = models.ImageField(upload_to="profiles/", null=True, blank=True)
    unique_doctor_code = models.CharField(max_length=32, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_version = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "registered_professionals"

class Question(models.Model):
    question_code = models.CharField(primary_key=True, max_length=64)
    display_order = models.IntegerField(unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "questions"

class QuestionI18n(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_column="question_code")
    lang = models.ForeignKey(Language, on_delete=models.RESTRICT, db_column="lang_code")
    question_text = models.TextField()

    class Meta:
        db_table = "questions_i18n"
        unique_together = (("question", "lang"),)

class RedFlag(models.Model):
    red_flag_code = models.CharField(primary_key=True, max_length=64)
    education_url_slug = models.CharField(max_length=191, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "red_flags"

class RedFlagI18n(models.Model):
    red_flag = models.ForeignKey(RedFlag, on_delete=models.CASCADE, db_column="red_flag_code")
    lang = models.ForeignKey(Language, on_delete=models.RESTRICT, db_column="lang_code")
    parent_label = models.CharField(max_length=255)

    class Meta:
        db_table = "red_flags_i18n"
        unique_together = (("red_flag", "lang"),)

class DoctorEducation(models.Model):
    red_flag = models.ForeignKey(RedFlag, on_delete=models.CASCADE, db_column="red_flag_code")
    lang = models.ForeignKey(Language, on_delete=models.RESTRICT, db_column="lang_code")
    education_markdown = models.TextField()  # MEDIUMTEXT in DB
    reference_1 = models.CharField(max_length=512, null=True, blank=True)
    reference_2 = models.CharField(max_length=512, null=True, blank=True)

    class Meta:
        db_table = "doctor_education"
        unique_together = (("red_flag", "lang"),)

class Option(models.Model):
    option_code = models.CharField(primary_key=True, max_length=80)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, db_column="question_code")
    display_order = models.IntegerField()
    triggers_red_flag = models.BooleanField(default=False)
    red_flag = models.ForeignKey(RedFlag, on_delete=models.RESTRICT, null=True, blank=True, db_column="red_flag_code")

    class Meta:
        db_table = "options"
        unique_together = (("question", "display_order"),)

class OptionI18n(models.Model):
    option = models.ForeignKey(Option, on_delete=models.CASCADE, db_column="option_code")
    lang = models.ForeignKey(Language, on_delete=models.RESTRICT, db_column="lang_code")
    option_text = models.CharField(max_length=255)

    class Meta:
        db_table = "options_i18n"
        unique_together = (("option", "lang"),)

class ResultMessage(models.Model):
    message_code = models.CharField(max_length=64)
    lang = models.ForeignKey(Language, on_delete=models.RESTRICT, db_column="lang_code")
    message_text = models.TextField()

    class Meta:
        db_table = "result_messages"
        unique_together = (("message_code", "lang"),)

class UiString(models.Model):
    key = models.CharField(max_length=64)
    lang = models.ForeignKey(Language, on_delete=models.RESTRICT, db_column="lang_code")
    text = models.TextField()

    class Meta:
        db_table = "ui_strings"
        unique_together = (("key", "lang"),)

# ===== Submissions (no PII) =====
class Submission(models.Model):
    report_code = models.CharField(max_length=32, unique=True)
    professional = models.ForeignKey(RegisteredProfessional, on_delete=models.RESTRICT)
    lang = models.ForeignKey(Language, on_delete=models.RESTRICT, db_column="lang_code")
    flags_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    email_to = models.CharField(max_length=191)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    sendgrid_message_id = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        db_table = "submissions"

class SubmissionAnswer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.RESTRICT, db_column="question_code")
    option = models.ForeignKey(Option, on_delete=models.RESTRICT, db_column="option_code")
    triggers_red_flag = models.BooleanField()
    red_flag = models.ForeignKey(RedFlag, on_delete=models.RESTRICT, null=True, blank=True, db_column="red_flag_code")

    class Meta:
        db_table = "submission_answers"
        unique_together = (("submission", "question"),)

class SubmissionRedFlag(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    red_flag = models.ForeignKey(RedFlag, on_delete=models.RESTRICT, db_column="red_flag_code")

    class Meta:
        db_table = "submission_red_flags"
        unique_together = (("submission", "red_flag"),)
