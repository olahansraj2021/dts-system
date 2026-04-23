from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)

    def __str__(self):
        return self.user.username


class Document(models.Model):
    doc_number = models.CharField(max_length=50, unique=True, blank=True)
    ref_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    subject = models.TextField()
    sender = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    related_name='sent_documents')

    department = models.ForeignKey( Department, on_delete=models.SET_NULL, null=True, blank=True)
    current_holder = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    related_name='assigned_documents')

    DOCUMENT_TYPES = [
    ('office_order', 'Office Order'),
    ('notification', 'Notification'),
    ('circular', 'Circular'),
    ('note', 'Note'),
    ('correspondence', 'Correspondence to Outside Party'),
    ('other', 'Others'),]

    doc_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    doc_type_other = models.CharField(max_length=100, blank=True, null=True)

    sender_department = models.ForeignKey(
    Department,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="incoming_docs")

    sender_other = models.CharField(max_length=100, blank=True, null=True)

    date_received = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=50, default="Received")
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(
    max_length=10,
    choices=[('Normal','Normal'), ('Urgent','Urgent')],
    default='Normal')
    approval_pending = models.BooleanField(default=False)
    external_approver = models.CharField(max_length=100, blank=True, null=True)
    is_external = models.BooleanField(default=False)
    def __str__(self):
        return self.doc_number

    def save(self, *args, **kwargs):
     if not self.doc_number:
        last = Document.objects.order_by('id').last()

        if last and last.doc_number:
            try:
                num = int(last.doc_number.split('/')[-1]) + 1
            except:
                num = 1
        else:
            num = 1
        self.doc_number = f"Admin/2026/{num:03d}"
     super().save(*args, **kwargs)


class Movement(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)

    from_user = models.ForeignKey(User, related_name='from_user', on_delete=models.SET_NULL, null=True)
    to_user = models.ForeignKey(User, related_name='to_user', on_delete=models.SET_NULL, null=True)

    action = models.CharField(max_length=50)
    remarks = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.doc_number} - {self.action}"
from django.contrib.auth.models import User
from django.db import models

class Workflow(models.Model):
    document = models.ForeignKey('Document', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_docs')
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL,null=True, blank=True,related_name='received_docs')
    action = models.CharField(max_length=20)  # Forward / Approved / Rejected
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document} - {self.action}"