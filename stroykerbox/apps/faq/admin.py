from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget

from .models import Question


class QuestionAdminForm(forms.ModelForm):
    question = forms.CharField(widget=CKEditorWidget())
    answer = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Question
        exclude = []


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'published', 'frontpage', 'position')
    list_editable = ('published', 'frontpage', 'position')

    form = QuestionAdminForm

    def question_text(self, obj):
        if obj:
            return str(obj)
