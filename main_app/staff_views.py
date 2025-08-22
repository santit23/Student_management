import json

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django.db.models import Avg, Max, Min, StdDev, Count

from .forms import *
from .models import *


def staff_home(request):
    staff = get_object_or_404(Staff, admin=request.user)
    total_students = Student.objects.filter(course=staff.course).count()
    total_leave = LeaveReportStaff.objects.filter(staff=staff).count()
    subjects = Subject.objects.filter(staff=staff)
    total_subject = subjects.count()
    attendance_list = Attendance.objects.filter(subject__in=subjects)
    total_attendance = attendance_list.count()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name)
        attendance_list.append(attendance_count)
    context = {
        'page_title': 'Staff Panel - ' + str(staff.admin.last_name) + ' (' + str(staff.course) + ')',
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_leave': total_leave,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list
    }
    return render(request, 'staff_template/home_content.html', context)


def staff_take_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Take Attendance'
    }

    return render(request, 'staff_template/staff_take_attendance.html', context)


@csrf_exempt
def get_students(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        students = Student.objects.filter(
            course_id=subject.course.id, session=session)
        student_data = []
        for student in students:
            data = {
                    "id": student.id,
                    "name": student.admin.last_name + " " + student.admin.first_name
                    }
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e



@csrf_exempt
def save_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    students = json.loads(student_data)
    try:
        session = get_object_or_404(Session, id=session_id)
        subject = get_object_or_404(Subject, id=subject_id)

        # Check if an attendance object already exists for the given date and session
        attendance, created = Attendance.objects.get_or_create(session=session, subject=subject, date=date)

        for student_dict in students:
            student = get_object_or_404(Student, id=student_dict.get('id'))

            # Check if an attendance report already exists for the student and the attendance object
            attendance_report, report_created = AttendanceReport.objects.get_or_create(student=student, attendance=attendance)

            # Update the status only if the attendance report was newly created
            if report_created:
                attendance_report.status = student_dict.get('status')
                attendance_report.save()

    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_update_attendance(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff_id=staff)
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'Update Attendance'
    }

    return render(request, 'staff_template/staff_update_attendance.html', context)


@csrf_exempt
def get_student_attendance(request):
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        date = get_object_or_404(Attendance, id=attendance_date_id)
        attendance_data = AttendanceReport.objects.filter(attendance=date)
        student_data = []
        for attendance in attendance_data:
            data = {"id": attendance.student.admin.id,
                    "name": attendance.student.admin.last_name + " " + attendance.student.admin.first_name,
                    "status": attendance.status}
            student_data.append(data)
        return JsonResponse(json.dumps(student_data), content_type='application/json', safe=False)
    except Exception as e:
        return e


@csrf_exempt
def update_attendance(request):
    student_data = request.POST.get('student_ids')
    date = request.POST.get('date')
    students = json.loads(student_data)
    try:
        attendance = get_object_or_404(Attendance, id=date)

        for student_dict in students:
            student = get_object_or_404(
                Student, admin_id=student_dict.get('id'))
            attendance_report = get_object_or_404(AttendanceReport, student=student, attendance=attendance)
            attendance_report.status = student_dict.get('status')
            attendance_report.save()
    except Exception as e:
        return None

    return HttpResponse("OK")


def staff_apply_leave(request):
    form = LeaveReportStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStaff.objects.filter(staff=staff),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('staff_apply_leave'))
            except Exception:
                messages.error(request, "Could not apply!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_apply_leave.html", context)


def staff_feedback(request):
    form = FeedbackStaffForm(request.POST or None)
    staff = get_object_or_404(Staff, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStaff.objects.filter(staff=staff),
        'page_title': 'Add Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.staff = staff
                obj.save()
                messages.success(request, "Feedback submitted for review")
                return redirect(reverse('staff_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "staff_template/staff_feedback.html", context)


def staff_view_profile(request):
    staff = get_object_or_404(Staff, admin=request.user)
    form = StaffEditForm(request.POST or None, request.FILES or None,instance=staff)
    context = {'form': form, 'page_title': 'View/Update Profile'}
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = staff.admin
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
                staff.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('staff_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
                return render(request, "staff_template/staff_view_profile.html", context)
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
            return render(request, "staff_template/staff_view_profile.html", context)

    return render(request, "staff_template/staff_view_profile.html", context)


@csrf_exempt
def staff_fcmtoken(request):
    token = request.POST.get('token')
    try:
        staff_user = get_object_or_404(CustomUser, id=request.user.id)
        staff_user.fcm_token = token
        staff_user.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def staff_view_notification(request):
    staff = get_object_or_404(Staff, admin=request.user)
    notifications = NotificationStaff.objects.filter(staff=staff)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "staff_template/staff_view_notification.html", context)


def staff_add_result(request):
    staff = get_object_or_404(Staff, admin=request.user)
    subjects = Subject.objects.filter(staff=staff)
    sessions = Session.objects.all()
    context = {
        'page_title': 'Result Upload',
        'subjects': subjects,
        'sessions': sessions
    }
    if request.method == 'POST':
        try:
            student_id = request.POST.get('student_list')
            subject_id = request.POST.get('subject')
            test = request.POST.get('test')
            exam = request.POST.get('exam')
            student = get_object_or_404(Student, id=student_id)
            subject = get_object_or_404(Subject, id=subject_id)
            try:
                data = StudentResult.objects.get(
                    student=student, subject=subject)
                data.exam = exam
                data.test = test
                data.save()
                messages.success(request, "Scores Updated")
            except:
                result = StudentResult(student=student, subject=subject, test=test, exam=exam)
                result.save()
                messages.success(request, "Scores Saved")
        except Exception as e:
            messages.warning(request, "Error Occured While Processing Form")
    return render(request, "staff_template/staff_add_result.html", context)


@csrf_exempt
def fetch_student_result(request):
    try:
        subject_id = request.POST.get('subject')
        student_id = request.POST.get('student')
        student = get_object_or_404(Student, id=student_id)
        subject = get_object_or_404(Subject, id=subject_id)
        result = StudentResult.objects.get(student=student, subject=subject)
        result_data = {
            'exam': result.exam,
            'test': result.test
        }
        return HttpResponse(json.dumps(result_data))
    except Exception as e:
        return HttpResponse('False')
    
@login_required
def quiz_list(request):
    """Show all quizzes created by this staff."""
    staff = get_object_or_404(Staff, admin=request.user)
    quizzes = Quiz.objects.filter(created_by=staff)
    return render(request, "staff_template/quiz_list.html", {"quizzes": quizzes})

@login_required
def quiz_create(request):
    """Staff creates a new quiz."""
    staff = get_object_or_404(Staff, admin=request.user)
    if request.method == "POST":
        form = QuizForm(request.POST, staff=staff)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = staff
            quiz.save()
            messages.success(request, f"Quiz '{quiz.title}' created. Now add questions.")
            # REDIRECT TO THE NEW BUILDER VIEW
            return redirect("quiz_detail", quiz_id=quiz.id)
        else: 
            messages.error(request, "Invalid Data Provided")
    else:
        form = QuizForm(staff=staff)

    context = {
        'form': form,
        'page_title': 'Create New Quiz (Step 1 of 2)'
    }
    return render(request, "staff_template/quiz_form.html", context)

@login_required
def quiz_detail(request, quiz_id):
    """View quiz details and its questions."""
    # Ensure the staff can only see their own quizzes
    staff = get_object_or_404(Staff, admin=request.user)
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=staff)
    
    # questions = quiz.questions.all()
    questions = quiz.questions.prefetch_related('choices').all()
    sessions = quiz.sessions.all()
    
    context = {
        "quiz": quiz, 
        "questions": questions,
        "page_title": f"Manage Quiz: {quiz.title}" # Add page title
    }
    
    # Make sure this path is correct for your project
    return render(request, "staff_template/quiz_detail.html", context)

@login_required
def question_add(request, quiz_id):
    """Add a question to quiz."""
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by__admin=request.user)
    question_form = QuestionForm(request.POST or None)
    choice_formset = ChoiceFormSet(request.POST or None, prefix='choices')

    if request.method == "POST":
        if question_form.is_valid() and choice_formset.is_valid():
            # First, save the question so we have an ID to link choices to
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.save()

            # Now, associate the formset with the saved question and save it
            choice_formset.instance = question
            choice_formset.save()

            messages.success(request, "Question and choices added successfully.")
            return redirect("quiz_detail", quiz_id=quiz.id)
        else:
            messages.error(request, "Please correct the errors below.")

    context = {
        "quiz": quiz,
        "question_form": question_form,
        "choice_formset": choice_formset,
        'page_title': f'Add Question to {quiz.title}'
    }
    return render(request, "staff_template/question_form.html", context)


@login_required
def choice_add(request, question_id):
    """Add a choice to a question."""
    question = get_object_or_404(Question, id=question_id, quiz__created_by=request.user)

    if request.method == "POST":
        form = ChoiceForm(request.POST)
        if form.is_valid():
            choice = form.save(commit=False)
            choice.question = question
            choice.save()
            messages.success(request, "Choice added.")
            return redirect("quiz_detail", quiz_id=question.quiz.id)
    else:
        form = ChoiceForm()

    return render(request, "staff_template/choice_form.html", {"form": form, "question": question})


@login_required
def quiz_session_create(request, quiz_id):
    """Create a new quiz session for a quiz."""
    staff = get_object_or_404(Staff, admin=request.user)
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=staff)

    if request.method == "POST":
        form = QuizSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.quiz = quiz
            session.created_by = staff
            session.save()
            messages.success(request, f"Session created with code {session.session_code}")
            return redirect("session_detail", session_id=session.id)
        else:
            # Add an error message so the user knows the submission failed
            messages.error(request, "Please correct the errors shown below.")
    else:
        form = QuizSessionForm()

    return render(request, "staff_template/session_form.html", {"form": form, "quiz": quiz, "page_title": f"Create Session for {quiz.title}"})



@login_required
def session_detail(request, session_id):
    """View session details (code + QR)."""
    staff = get_object_or_404(Staff, admin=request.user)
    session = get_object_or_404(QuizSession, id=session_id, created_by=staff)
    return render(request, "staff_template/session_detail.html", {"session": session, "page title": "Live Session Details"})


@login_required
def quiz_builder(request, quiz_id):
    """
    A dedicated page to add multiple questions and choices to a specific quiz.
    """
    staff = get_object_or_404(Staff, admin=request.user)
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=staff)

    # Create a formset class that uses our custom form, showing 1 empty form
    QuestionFormSet = formset_factory(QuestionAndChoicesForm, extra=1)

    if request.method == 'POST':
        formset = QuestionFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                # Extract data from the form
                question_text = form.cleaned_data.get('text')
                marks = form.cleaned_data.get('marks')
                choices_data = [
                    form.cleaned_data.get('choice_1'),
                    form.cleaned_data.get('choice_2'),
                    form.cleaned_data.get('choice_3'),
                    form.cleaned_data.get('choice_4'),
                ]
                correct_choice_index = int(form.cleaned_data.get('correct_choice')) - 1

                # Create Question and Choice objects in the database
                if question_text:
                    question = Question.objects.create(quiz=quiz, text=question_text, marks=marks)
                    for i, choice_text in enumerate(choices_data):
                        if choice_text:
                            is_correct = (i == correct_choice_index)
                            Choice.objects.create(question=question, text=choice_text, is_correct=is_correct)
            
            messages.success(request, "Questions added successfully!")
            return redirect('quiz_detail', quiz_id=quiz.id)
    else:
        formset = QuestionFormSet()

    context = {
        'quiz': quiz,
        'formset': formset,
        'page_title': f'Add Questions to: {quiz.title}'
    }
    return render(request, 'staff_template/quiz_builder.html', context)

# @login_required
# def session_dashboard(request, session_id):
#     """
#     Displays a live dashboard for a quiz session, showing student progress and scores.
#     """
#     staff = get_object_or_404(Staff, admin=request.user)
#     session = get_object_or_404(QuizSession, id=session_id, created_by=staff)

#     attempts = session.attempts.select_related('student').all()

#     # Calculate summary statistics
#     total_students_joined = attempts.count()
#     submitted_attempts = attempts.filter(status=QuizAttempt.STATUS_SUBMITTED)
#     completed_count = submitted_attempts.count()
    
#     # Calculate average score, handling the case where no one has submitted yet
#     average_score_data = submitted_attempts.aggregate(average_score=Avg('score'))
#     average_score = average_score_data.get('average_score')
#     if average_score is not None:
#         average_score = round(average_score, 2) # Round to 2 decimal places

#     context = {
#         'session': session,
#         'attempts': attempts,
#         'total_students_joined': total_students_joined,
#         'completed_count': completed_count,
#         'average_score': average_score,
#         'page_title': f"Dashboard: {session.quiz.title}"
#     }
#     return render(request, 'staff_template/session_dashboard.html', context)


# Add these to your imports at the top
from django.db.models import Avg, Max, Min, StdDev, Count

# In staff_view.py

from django.db.models import Avg, Max, Min, StdDev, Count # Make sure these are imported

@login_required
def session_dashboard(request, session_id):
    """
    Displays a rich analysis dashboard for a quiz session, including performance stats and charts.
    """
    staff = get_object_or_404(Staff, admin=request.user)
    session = get_object_or_404(QuizSession, id=session_id, created_by=staff)
    
    # --- THIS IS THE FIX ---
    # Calculate total_marks_possible early, as it's always needed.
    total_marks_possible = sum(q.marks for q in session.quiz.questions.all())
    
    # Get all submitted attempts for this session
    submitted_attempts = session.attempts.filter(status=QuizAttempt.STATUS_SUBMITTED).select_related('student__admin')

    # Handle the case where there are no submissions yet
    if not submitted_attempts.exists():
        context = {
            'session': session,
            'page_title': f"Dashboard: {session.quiz.title}",
            'no_submissions': True,
            # Pass a default value for total_marks_possible even if no one took the quiz
            'total_marks_possible': total_marks_possible, 
        }
        return render(request, 'staff_template/session_dashboard.html', context)

    # --- Calculations for when submissions EXIST ---
    
    # Avoid division by zero if a quiz has no marks
    safe_total_marks = total_marks_possible if total_marks_possible > 0 else 1

    performance_stats = submitted_attempts.aggregate(
        avg_score=Avg('score'),
        max_score=Max('score'),
        min_score=Min('score'),
        std_dev=StdDev('score')
    )

    total_students_in_course = Student.objects.filter(course=session.quiz.subject.course).count()
    total_students_joined = submitted_attempts.values('student').distinct().count()
    participation_rate = (total_students_joined / total_students_in_course) * 100 if total_students_in_course > 0 else 0

    score_percentages = [ (attempt.score / safe_total_marks) * 100 for attempt in submitted_attempts ]
    bins = [0] * 10 
    for p in score_percentages:
        index = min(int(p / 10), 9)
        if p == 0:
            bins[0] += 1
        elif index > 0:
            bins[index] +=1
        else:
            bins[0] +=1

    histogram_data = {
        'labels': ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"],
        'data': bins
    }

    context = {
        'session': session,
        'page_title': f"Analysis for {session.quiz.title}",
        'no_submissions': False,
        'performance_stats': performance_stats,
        'total_marks_possible': total_marks_possible,
        'total_students_joined': total_students_joined,
        'participation_rate': participation_rate,
        'histogram_data': histogram_data,
        'student_attempts': submitted_attempts.order_by('-score'),
    }
    return render(request, 'staff_template/session_dashboard.html', context)

@login_required
def item_analysis(request, session_id):
    """
    Provides a detailed, question-by-question analysis for a quiz session.
    """
    staff = get_object_or_404(Staff, admin=request.user)
    session = get_object_or_404(QuizSession, id=session_id, created_by=staff)
    
    # Get all submitted attempts for this session
    attempts = session.attempts.filter(status=QuizAttempt.STATUS_SUBMITTED)
    
    if not attempts.exists():
        messages.warning(request, "There are no student submissions to analyze for this session yet.")
        return redirect('session_dashboard', session_id=session.id)

    questions = session.quiz.questions.prefetch_related('choices').all()
    
    item_analysis_data = []
    for question in questions:
        # Get all answers for this specific question from all attempts in this session
        answers_for_question = Answer.objects.filter(attempt__in=attempts, question=question)
        total_answers = answers_for_question.count()

        if total_answers > 0:
            # Calculate how many students answered this question correctly
            correct_answers = answers_for_question.filter(selected_choice__is_correct=True).count()
            difficulty_percentage = (correct_answers / total_answers) * 100
            
            # Calculate how many students chose each specific option
            choice_stats = []
            for choice in question.choices.all():
                times_selected = answers_for_question.filter(selected_choice=choice).count()
                selection_percentage = (times_selected / total_answers) * 100
                choice_stats.append({
                    'text': choice.text,
                    'is_correct': choice.is_correct,
                    'times_selected': times_selected,
                    'selection_percentage': selection_percentage
                })
        else:
            difficulty_percentage = None
            choice_stats = []

        item_analysis_data.append({
            'question': question,
            'difficulty_percentage': difficulty_percentage,
            'choice_stats': choice_stats
        })

    context = {
        'session': session,
        'item_analysis_data': item_analysis_data,
        'page_title': f"Item Analysis for {session.quiz.title}"
    }
    return render(request, 'staff_template/item_analysis.html', context)