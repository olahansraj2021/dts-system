from django.contrib import admin
from .models import Department, Profile, Document, Workflow

admin.site.register(Department)
admin.site.register(Profile)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('doc_number', 'status', 'current_holder', 'created_at')
    search_fields = ('doc_number',)
    list_filter = ('status',)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('document', 'sender', 'receiver', 'action', 'timestamp')
    list_filter = ('action',)