from django import forms
from django.forms.widgets import DateInput, TextInput
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import *


class FormSettings(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormSettings, self).__init__(*args, **kwargs)
        # Here make some changes such as:
        for field in self.visible_fields():
            field.field.widget.attrs['class'] = 'form-control'


class CustomUserForm(FormSettings):
    email = forms.EmailField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')])
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea)
    password = forms.CharField(widget=forms.PasswordInput)
    widget = {
        'password': forms.PasswordInput(),
    }
    profile_pic = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)

        if kwargs.get('instance'):
            instance = kwargs.get('instance').admin.__dict__
            self.fields['password'].required = False
            for field in CustomUserForm.Meta.fields:
                self.fields[field].initial = instance.get(field)
            if self.instance.pk is not None:
                self.fields['password'].widget.attrs['placeholder'] = "Fill this only if you wish to update password"

    def clean_email(self, *args, **kwargs):
        formEmail = self.cleaned_data['email'].lower()
        if self.instance.pk is None:  # Insert
            if CustomUser.objects.filter(email=formEmail).exists():
                raise forms.ValidationError(
                    "The given email is already registered")
        else:  # Update
            dbEmail = self.Meta.model.objects.get(
                id=self.instance.pk).admin.email.lower()
            if dbEmail != formEmail:  # There has been changes
                if CustomUser.objects.filter(email=formEmail).exists():
                    raise forms.ValidationError("The given email is already registered")

        return formEmail

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'gender',  'password','profile_pic', 'address' ]


class StudentForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StudentForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields + \
            ['course', 'session']


class AdminForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Admin
        fields = CustomUserForm.Meta.fields


class StaffForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StaffForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields + \
            ['course' ]


class CourseForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['name']
        model = Course


class SubjectForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Subject
        fields = ['name', 'staff', 'course']


class SessionForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(SessionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Session
        fields = '__all__'
        widgets = {
            'start_year': DateInput(attrs={'type': 'date'}),
            'end_year': DateInput(attrs={'type': 'date'}),
        }


class LeaveReportStaffForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStaff
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackStaffForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStaff
        fields = ['feedback']


class LeaveReportStudentForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStudent
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


class FeedbackStudentForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStudent
        fields = ['feedback']


class StudentEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StudentEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields 


class StaffEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StaffEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields


class EditResultForm(FormSettings):
    session_list = Session.objects.all()
    session_year = forms.ModelChoiceField(
        label="Session Year", queryset=session_list, required=True)

    def __init__(self, *args, **kwargs):
        super(EditResultForm, self).__init__(*args, **kwargs)

    class Meta:
        model = StudentResult
        fields = ['session_year', 'subject', 'student', 'test', 'exam']


class QuizForm(forms.ModelForm):
    # Make the description field a textarea
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    class Meta:
        model = Quiz
        fields = ["subject", "title", "description", "duration_minutes"]
        
    def __init__(self, *args, **kwargs):
        # Pop the 'staff' object passed from the view
        staff = kwargs.pop('staff', None)
        super().__init__(*args, **kwargs)

        # If a staff member was passed in, filter the 'subject' field's queryset
        if staff:
            self.fields['subject'].queryset = Subject.objects.filter(staff=staff)
        else:
            self.fields['subject'].queryset = Subject.objects.none()

# This is a validation class for our formset
class BaseChoiceFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        # Check that at least one choice has been marked as correct.
        has_correct_choice = False
        for form in self.forms:
            if not form.is_valid():
                # Don't run validation on invalid forms
                continue
            if form.cleaned_data.get('is_correct') and not form.cleaned_data.get('DELETE', False):
                has_correct_choice = True
                break
        
        if not has_correct_choice:
            raise forms.ValidationError("You must select at least one correct answer.", code='no_correct_answer')

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["text", "question_type", "marks", "order"]

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ["text", "is_correct"]

class QuizSessionForm(forms.ModelForm):
    class Meta:
        model = QuizSession
        fields = ['starts_at', 'ends_at', 'max_attempts_per_student', 'is_active']

        widgets = {
            'starts_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'  # This format matches the datetime-local input
            ),
            'ends_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'},
                format='%Y-%m-%dT%H:%M'
            ),
            'max_attempts_per_student': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1, 'value': 1}
            ),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make the time fields optional, as they can be blank
        self.fields['starts_at'].required = False
        self.fields['ends_at'].required = False

# This is the formset factory for linking Choices to a Question
# It will generate multiple choice forms on the question page
ChoiceFormSet = inlineformset_factory(
    Question,                   # Parent model
    Choice,                     # Child model
    formset=BaseChoiceFormSet,  # Use our custom validation
    fields=('text', 'is_correct'), # Fields to include in each choice form
    extra=4,                    # Show 4 empty choice forms by default
    can_delete=True,            # Allow deleting choices
    min_num=1,                  # Require at least one choice to be submitted
    validate_min=True,
)

class QuestionAndChoicesForm(forms.Form):
    """
    A form to handle one Question and its Choices. We will use this in a formset.
    """
    text = forms.CharField(
        label="Question Text",
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
    )
    marks = forms.FloatField(initial=1.0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    
    # Define fields for 4 choices
    choice_1 = forms.CharField(label="Choice 1", widget=forms.TextInput(attrs={'class': 'form-control'}))
    choice_2 = forms.CharField(label="Choice 2", widget=forms.TextInput(attrs={'class': 'form-control'}))
    choice_3 = forms.CharField(label="Choice 3", widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    choice_4 = forms.CharField(label="Choice 4", widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)

    # Field to select the correct answer
    CORRECT_CHOICE_OPTIONS = [
        ('1', 'Choice 1'),
        ('2', 'Choice 2'),
        ('3', 'Choice 3'),
        ('4', 'Choice 4'),
    ]
    correct_choice = forms.ChoiceField(
        label="Correct Answer",
        choices=CORRECT_CHOICE_OPTIONS,
        widget=forms.RadioSelect
    )

