from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from django.contrib.auth.models import AbstractUser
import secrets
from io import BytesIO
from django.core.files import File
from django.utils import timezone
from django.utils.crypto import get_random_string

import qrcode  # Ensure you have the qrcode library installed: pip install qrcode[pil]





class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = CustomUser(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        assert extra_fields["is_staff"]
        assert extra_fields["is_superuser"]
        return self._create_user(email, password, **extra_fields)


class Session(models.Model):
    start_year = models.DateField()
    end_year = models.DateField()

    def __str__(self):
        return "From " + str(self.start_year) + " to " + str(self.end_year)


class CustomUser(AbstractUser):
    USER_TYPE = ((1, "HOD"), (2, "Staff"), (3, "Student"))
    GENDER = [("M", "Male"), ("F", "Female")]
    
    
    username = None  # Removed username, using email instead
    email = models.EmailField(unique=True)
    user_type = models.CharField(default=1, choices=USER_TYPE, max_length=1)
    gender = models.CharField(max_length=1, choices=GENDER)
    profile_pic = models.ImageField()
    address = models.TextField()
    fcm_token = models.TextField(default="")  # For firebase notifications
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return self.last_name + ", " + self.first_name


class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)



class Course(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Student(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=False)
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING, null=True)

    def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name


class Staff(models.Model):
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=False)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.last_name + " " + self.admin.first_name


class Subject(models.Model):
    name = models.CharField(max_length=120)
    staff = models.ForeignKey(Staff,on_delete=models.CASCADE,)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Attendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    subject = models.ForeignKey(Subject, on_delete=models.DO_NOTHING)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AttendanceReport(models.Model):
    student = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveReportStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FeedbackStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NotificationStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StudentResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    test = models.FloatField(default=0)
    exam = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            Admin.objects.create(admin=instance)
        if instance.user_type == 2:
            Staff.objects.create(admin=instance)
        if instance.user_type == 3:
            Student.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.admin.save()
    if instance.user_type == 2:
        instance.staff.save()
    if instance.user_type == 3:
        instance.student.save()

class Quiz(models.Model):
    """
    Quiz created by staff for specific subject.
    """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="quizzes")  
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=10)
    created_by = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="quizzes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
         

    def __str__(self):
        return self.title
    
class Question(models.Model):
    """
    Defaulting to single-correct MCQ; extensible later.
    """
    SINGLE_CHOICE = "single"
    MULTI_CHOICE = "multi"
    TEXT = "text"

    QUESTION_TYPES = [
        (SINGLE_CHOICE, "Single choice"),
        (MULTI_CHOICE, "Multiple choice"),
        (TEXT, "Text answer"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default=SINGLE_CHOICE)
    marks = models.FloatField(default=1.0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Q{self.order or self.id}: {self.text[:50]}..."
    

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{'✔' if self.is_correct else '✘'} {self.text[:40]}"
    
def _generate_session_code():
    """
    Generates an unambiguous 6-char code (A-Z, 2-9) and ensures uniqueness.
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I/O/1/0
    while True:
        code = get_random_string(6, allowed_chars=alphabet)
        if not QuizSession.objects.filter(session_code=code).exists():
            return code

class QuizSession(models.Model):
    """
    A joinable/live session for a quiz. The save() method handles code generation.
    """
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="sessions")
    created_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="quiz_sessions")
    session_code = models.CharField(max_length=10, unique=True, db_index=True, blank=True)
    qr_code = models.ImageField(upload_to="quiz_sessions/qrcodes/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    max_attempts_per_student = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_open_now(self):
        """
        Returns True if the session is active and the current time is
        within the optional start and end times.
        """
        now = timezone.now()
        if not self.is_active:
            return False
        # If a start time is set, the session is not open yet if 'now' is before it.
        if self.starts_at and now < self.starts_at:
            return False
        # If an end time is set, the session is closed if 'now' is after it.
        if self.ends_at and now > self.ends_at:
            return False
        # Otherwise, the session is open.
        return True

    def __str__(self):
        return f"{self.quiz.title} [{self.session_code}]"

    def save(self, *args, **kwargs):
        # --- THIS IS THE CRITICAL LOGIC ---
        # 1. Generate a unique session code ONLY when creating a new session.
        if not self.pk: # self.pk is None if the object is new
            self.session_code = _generate_session_code()

        # 2. Call the original save() method to save the object and session_code to the DB.
        super().save(*args, **kwargs)

        # 3. Generate a QR code ONLY if one doesn't already exist.
        if not self.qr_code:
            try:
                # The data for the QR code is the session code itself
                qr_img = qrcode.make(self.session_code)
                
                # Save the generated image to a temporary buffer in memory
                buffer = BytesIO()
                qr_img.save(buffer, format="PNG")
                filename = f"{self.session_code}.png"
                
                # Save the buffer's content to the ImageField without calling save() again
                self.qr_code.save(filename, File(buffer), save=False)
                
                # Now, update ONLY the qr_code field in the database in a separate, efficient query.
                super().save(update_fields=['qr_code'])

            except ImportError:
                # If the qrcode library isn't installed, this will prevent a crash.
                pass


class QuizAttempt(models.Model):
    """
    A student's attempt in a given session. Default allowing 1 attempt.
    """
    STATUS_STARTED = "started"
    STATUS_SUBMITTED = "submitted"
    STATUS_CANCELLED = "cancelled"

    STATUSES = [
        (STATUS_STARTED, "Started"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="quiz_attempts")
    attempt_no = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=12, choices=STATUSES, default=STATUS_STARTED)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    score = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("session", "student", "attempt_no")
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.student} → {self.session.session_code} (#{self.attempt_no})"

class Answer(models.Model):
    """
    Stores each answer for an attempt.
    For MCQ-single: use selected_choice.
    For text: use text_answer.
    For MCQ-multi: multiple Answer rows per question (or extend later with M2M).
    """
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    text_answer = models.TextField(blank=True)

    class Meta:
        unique_together = ("attempt", "question")

    def __str__(self):
        return f"Ans: {self.question_id} by Attempt {self.attempt_id}"