import json
import math
import requests
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .forms import *
from .models import *

def student_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'user_type') or request.user.user_type != '3':
            return redirect('login') 
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def student_home(request):
    student = get_object_or_404(Student, admin=request.user)
    total_subject = Subject.objects.filter(course=student.course).count()
    total_attendance = AttendanceReport.objects.filter(student=student).count()
    total_present = AttendanceReport.objects.filter(student=student, status=True).count()
    if total_attendance == 0: 
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present/total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    subject_name = []
    data_present = []
    data_absent = []
    subjects = Subject.objects.filter(course=student.course)
    for subject in subjects:
        attendance = Attendance.objects.filter(subject=subject)
        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, student=student).count()
        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, student=student).count()
        subject_name.append(subject.name)
        data_present.append(present_count)
        data_absent.append(absent_count)
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_subject': total_subject,
        'subjects': subjects,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': subject_name,
        'page_title': 'Student Homepage'

    }
    return render(request, 'student_template/home_content.html', context)


@ csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method != 'POST':
        course = get_object_or_404(Course, id=student.course.id)
        context = {
            'subjects': Subject.objects.filter(course=course),
            'page_title': 'View Attendance'
        }
        return render(request, 'student_template/student_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student=student)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'

    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
                if password != None:
                    admin.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, "Error Occured While Updating Profile " + str(e))

    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_result(request):
    student = get_object_or_404(Student, admin=request.user)
    results = StudentResult.objects.filter(student=student)
    context = {
        'results': results,
        'page_title': "View Results"
    }
    return render(request, "student_template/student_view_result.html", context)


# Quiz

def student_join_quiz(request):
    if request.method == 'POST':
        session_code = request.POST.get('session_code', '').strip().upper()
        
        if not session_code:
            messages.error(request, "Please enter a session code.")
            return redirect('student_join_quiz')

        try:
            quiz_session = QuizSession.objects.get(session_code=session_code)
            
            if not quiz_session.is_open_now:
                messages.error(request, "This quiz session is not currently active or has ended.")
                return redirect('student_join_quiz')
                
            return redirect('quiz_lobby', session_id=quiz_session.id)
            
        except QuizSession.DoesNotExist:
            messages.error(request, "Invalid session code. Please check the code and try again.")

    return render(request, 'student_template/join_quiz.html', {'page_title': 'Join a Quiz'})

@student_required
def quiz_lobby(request, session_id):
    """
    Displays quiz details and a 'Start' button before the quiz begins.
    Also checks if the student has already reached their max attempts.
    """
    session = get_object_or_404(QuizSession, id=session_id)
    student = get_object_or_404(Student, admin=request.user)
    
    existing_attempts = QuizAttempt.objects.filter(session=session, student=student).count()

    if existing_attempts >= session.max_attempts_per_student:
        messages.warning(request, "You have already completed the maximum number of attempts for this quiz.")
        return redirect('student_home') 

    context = {
        'session': session,
        'page_title': f"Ready to Start: {session.quiz.title}"
    }
    return render(request, 'student_template/quiz_lobby.html', context)

def get_client_ip(request):
    """A helper function to get the student's real IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    # For local development
    if ip == '127.0.0.1':
        ip = '124.41.204.21' 
    return ip

@student_required
def quiz_take(request, session_id):
    """
    Handles the main quiz-taking process, displaying questions and processing answers.
    """
    session = get_object_or_404(QuizSession, id=session_id)
    student = get_object_or_404(Student, admin=request.user)
    
    questions = session.quiz.questions.prefetch_related('choices').all()

    if request.method == 'POST':
        latitude, longitude = None, None
        try:
            ip_address = get_client_ip(request)
            
            response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=5)
            response.raise_for_status() 
            
            data = response.json()
            if not data.get('error'):
                latitude = data.get('latitude')
                longitude = data.get('longitude')
                print(f"Location found for IP {ip_address}: {latitude}, {longitude}")
        except Exception as e:
            print(f"Could not get location via IP address. Error: {e}")
        
        attempt = QuizAttempt.objects.create(
            session=session,
            student=student,
            status=QuizAttempt.STATUS_STARTED,
            attempt_no=QuizAttempt.objects.filter(session=session, student=student).count() + 1,
            latitude=latitude,
            longitude=longitude
        )
        
        total_score = 0
        for question in questions:
            submitted_choice_id = request.POST.get(f'question_{question.id}')
            if submitted_choice_id:
                selected_choice = get_object_or_404(Choice, id=submitted_choice_id)
                Answer.objects.create(attempt=attempt, question=question, selected_choice=selected_choice)
                if selected_choice.is_correct:
                    total_score += question.marks
        
        attempt.score = total_score
        attempt.status = QuizAttempt.STATUS_SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save()

        return redirect('quiz_result', attempt_id=attempt.id)

    context = {
        'session': session,
        'questions': questions,
        'page_title': f"Taking Quiz: {session.quiz.title}"
    }
    return render(request, 'student_template/quiz_take.html', context)


@student_required
def quiz_result(request, attempt_id):
    """
    Displays the final score to the student immediately after they submit their quiz.
    """
    student = get_object_or_404(Student, admin=request.user)
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, student=student)

    total_marks_possible = sum(q.marks for q in attempt.session.quiz.questions.all())

    context = {
        'attempt': attempt,
        'total_marks_possible': total_marks_possible,
        'page_title': 'Quiz Results'
    }
    return render(request, 'student_template/quiz_result.html', context)