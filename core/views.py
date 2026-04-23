from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.db.models import Q
from django.contrib import messages

from .models import Document, Workflow, Department, Movement


# ================= DASHBOARD =================
@login_required
def dashboard(request):
    user = request.user
    query = request.GET.get("q")

    assigned_docs = Document.objects.filter(current_holder=user).exclude(status__icontains="closed")
    created_docs = user.sent_documents.all()

    #  External docs (ONLY for Dispatch)
    external_docs = []
    if user.profile.role == "Dispatch":
        external_docs = Document.objects.filter(is_external=True)

    if query:
        assigned_docs = assigned_docs.filter(
            Q(subject__icontains=query) |
            Q(doc_number__icontains=query) |
            Q(sender__username__icontains=query) |
            Q(sender__first_name__icontains=query) |
            Q(sender__last_name__icontains=query)
        )

        created_docs = created_docs.filter(
            Q(subject__icontains=query) |
            Q(doc_number__icontains=query) |
            Q(current_holder__username__icontains=query) |
            Q(current_holder__first_name__icontains=query) |
            Q(current_holder__last_name__icontains=query)
        )

        #  search in external docs too
        if user.profile.role == "Dispatch":
            external_docs = external_docs.filter(
                Q(subject__icontains=query) |
                Q(doc_number__icontains=query)
            )

    pending_count = assigned_docs.count()

    return render(request, 'dashboard.html', {
        'assigned_docs': assigned_docs,
        'created_docs': created_docs,
        'pending_count': pending_count,
        'external_docs': external_docs 
    })


# ================= CREATE =================
@login_required
def create_document(request):

    if request.method == "POST":
        subject = request.POST.get("subject")
        first_user_id = request.POST.get("first_user")
        priority = request.POST.get("priority")
        ref_number = request.POST.get("ref_number")

        #  NEW FIELDS
        doc_type = request.POST.get("doc_type")
        doc_type_other = request.POST.get("doc_type_other")

        sender_type = request.POST.get("sender_type")
        sender_department_id = request.POST.get("sender_department")
        sender_other = request.POST.get("sender_other")

        date_received = request.POST.get("date_received")
        first_user = get_object_or_404(User, id=first_user_id)

        #  sender logic
        sender_department = None
        if sender_type == "department" and sender_department_id:
            sender_department = Department.objects.get(id=sender_department_id)

        doc = Document.objects.create(
            subject=subject,
            sender=request.user,
            current_holder=first_user,
            status=f"Marked to {first_user.get_full_name() or first_user.username}",
            priority=priority,
            ref_number=ref_number if ref_number else None,

            #  SAVE NEW DATA
            doc_type=doc_type,
            doc_type_other=doc_type_other if doc_type == "other" else None,

            sender_department=sender_department,
            sender_other=sender_other if sender_type == "other" else None,

            date_received=date_received
        )

        Workflow.objects.create(
            document=doc,
            sender=request.user,
            receiver=first_user,
            action="Marked",
            remarks="Initial dispatch"
        )

        Movement.objects.create(
            document=doc,
            from_user=request.user,
            to_user=first_user,
            action="Created & Assigned",
            remarks="Initial dispatch"
        )

        return redirect('dashboard')

    return render(request, 'create_document.html', {
        'departments': Department.objects.all(),
        'users': User.objects.exclude(id=request.user.id)
    })


# ================= FORWARD PAGE =================
@login_required
def forward_page(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    if doc.current_holder != request.user:
        return HttpResponse("Unauthorized", status=403)

    return render(request, 'forward.html', {
        'doc': doc,
        'users': User.objects.exclude(id=request.user.id)
    })


# ================= FORWARD ACTION =================
@login_required
def forward_document_view(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    if doc.current_holder != request.user:
        return HttpResponse("Unauthorized", status=403)

    if request.method == "POST":

        forward_type = request.POST.get("forward_type")
        user_id = request.POST.get("user_id")
        external_name = request.POST.get("external_name")
        remarks = request.POST.get("remarks", "")

        # ========= EXTERNAL =========
        if forward_type == "external" and external_name:
            doc.current_holder = None
            doc.status = f"Sent to {external_name}"
            doc.approval_pending = True
            doc.external_approver = external_name
            doc.is_external = True
            doc.save()

            Workflow.objects.create(
                document=doc,
                sender=request.user,
                receiver=None,
                action="Sent External",
                remarks=remarks
            )

            Movement.objects.create(
                document=doc,
                from_user=request.user,
                to_user=None,
                action="Forward to External",
                remarks=external_name
            )

        # ========= INTERNAL =========
        elif forward_type == "internal" and user_id:
            receiver = get_object_or_404(User, id=user_id)

            if receiver == request.user:
                return HttpResponse("Cannot forward to yourself", status=400)

            doc.current_holder = receiver
            doc.status = f"Forwarded to {receiver.get_full_name() or receiver.username}"
            doc.is_external = False
            doc.save()

            Workflow.objects.create(
                document=doc,
                sender=request.user,
                receiver=receiver,
                action="Forwarded",
                remarks=remarks
            )

            Movement.objects.create(
                document=doc,
                from_user=request.user,
                to_user=receiver,
                action="Forward",
                remarks=remarks
            )

        return redirect("dashboard")


# ================= EXTERNAL DECISION =================
@login_required
def external_decision(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    if not doc.approval_pending:
        return HttpResponse("No approval pending", status=400)

    if request.method == "POST":
        action = request.POST.get("action")  # approve / reject
        remarks = request.POST.get("remarks", "")

        dispatch_user = User.objects.filter(profile__role="Dispatch").first()

        if not dispatch_user:
            return HttpResponse("Dispatch user not found", status=500)

        if action == "approve":
            doc.status = f"Approved by {doc.external_approver}"
        elif action == "reject":
            doc.status = f"Rejected by {doc.external_approver}"

        doc.current_holder = dispatch_user
        doc.approval_pending = False
        doc.is_external = False
        doc.save()

        Workflow.objects.create(
            document=doc,
            sender=request.user,
            receiver=dispatch_user,
            action=action.capitalize(),
            remarks=remarks
        )

        Movement.objects.create(
            document=doc,
            from_user=request.user,
            to_user=dispatch_user,
            action=f"External {action}",
            remarks=remarks
        )

        return redirect("dashboard")

    return HttpResponse("Invalid request", status=400)


# ================= CLOSE =================
@login_required
def close_document(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    if doc.current_holder != request.user:
        return HttpResponse("Unauthorized", status=403)

    if request.method == "POST":
        remarks = request.POST.get("remarks", "")

        doc.status = "Closed"
        doc.save()

        Workflow.objects.create(
            document=doc,
            sender=request.user,
            receiver=request.user,
            action="Closed",
            remarks=remarks
        )

        Movement.objects.create(
            document=doc,
            from_user=request.user,
            to_user=request.user,
            action="Closed",
            remarks=remarks
        )

    return redirect('dashboard')


# ================= DETAIL =================
@login_required
def document_detail(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    history = Workflow.objects.filter(document=doc).order_by('-timestamp')
    movement = Movement.objects.filter(document=doc).order_by('-timestamp')

    return render(request, 'document_detail.html', {
        'doc': doc,
        'history': history,
        'movement': movement
    })


# ================= AUTH =================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password")
        )

        if user:
            login(request, user)
            return redirect('dashboard')

        return render(request, 'login.html', {
            'error': 'Invalid credentials'
        })

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ================= PROFILE =================
@login_required
def profile(request):
    user = request.user

    total_docs = user.sent_documents.count()
    assigned_docs = user.assigned_documents.count()
    closed_docs = Document.objects.filter(current_holder=user, status="Closed").count()
    pending_docs = assigned_docs - closed_docs

    activity = Workflow.objects.filter(sender=user).order_by('-timestamp')[:5]

    if request.method == "POST":
        old = request.POST.get("old_password")
        new = request.POST.get("new_password")

        if user.check_password(old):
            user.set_password(new)
            user.save()
            return redirect('login')
        else:
            return HttpResponse("Wrong password")

    return render(request, 'profile.html', {
        'total_docs': total_docs,
        'assigned_docs': assigned_docs,
        'closed_docs': closed_docs,
        'pending_docs': pending_docs,
        'activity': activity
    })
from django.http import JsonResponse

def tv_dashboard_api(request):
    docs = Document.objects.select_related('current_holder').order_by('-created_at')

    data = []
    for d in docs:
        data.append({
            "doc_no": d.doc_number,
            "status": d.status,
            "holder": d.current_holder.get_full_name() if d.current_holder else "External",
            "is_external": d.is_external,
            "created_at": d.created_at.strftime("%d-%m-%Y %H:%M")
        })

    return JsonResponse({"data": data})
def tv_dashboard_view(request):
    return render(request, "tv_dashboard.html")
from django.db.models import Q

@login_required
def sent_documents(request):
    docs = Document.objects.filter(
        Q(sender=request.user) | 
        Q(workflow__sender=request.user)
    ).distinct().order_by('-created_at')

    return render(request, 'sent_documents.html', {
        'documents': docs
    })
@login_required
def receive_back(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    # 🔐 Only Dispatch allowed
    if request.user.profile.role != "Dispatch":
        return HttpResponse("Unauthorized", status=403)

    # 🔒 Only external docs allowed
    if not doc.is_external:
        return HttpResponse("Not external document", status=400)

    # ✅ Receive back to dispatch
    doc.current_holder = request.user
    doc.is_external = False
    doc.approval_pending = False
    doc.status = "Received Back at Dispatch"
    doc.save()

    # 🧾 Workflow log
    Workflow.objects.create(
        document=doc,
        sender=request.user,
        receiver=request.user,
        action="Received Back",
        remarks="Returned from External Authority"
    )

    # 📊 Movement log
    Movement.objects.create(
        document=doc,
        from_user=None,
        to_user=request.user,
        action="External Return",
        remarks=f"Returned from {doc.external_approver}"
    )

    return redirect("dashboard")
@login_required
def receive_and_mark(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    if request.user.profile.role != "Dispatch":
        return HttpResponse("Unauthorized", status=403)

    # Step 1: Receive
    doc.current_holder = request.user
    doc.is_external = False
    doc.status = "Received Back at Dispatch"
    doc.save()

    # Step 2: redirect to forward page
    return redirect('forward_page', doc_id=doc.id)
@login_required
def receive_and_close(request, doc_id):
    doc = get_object_or_404(Document, id=doc_id)

    if request.user.profile.role != "Dispatch":
        return HttpResponse("Unauthorized", status=403)

    # Step 1: Receive
    doc.current_holder = request.user
    doc.is_external = False

    # Step 2: Close
    doc.status = "Closed"
    doc.save()

    Workflow.objects.create(
        document=doc,
        sender=request.user,
        receiver=request.user,
        action="Closed",
        remarks="Closed after external return"
    )

    return redirect('dashboard')
from django.http import HttpResponse
import csv

@login_required
def report_view(request):

    docs = Document.objects.all().order_by('-created_at')

    #  Filters
    doc_type = request.GET.get("doc_type")
    sender_dept = request.GET.get("sender_department")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if doc_type:
        docs = docs.filter(doc_type=doc_type)

    if sender_dept:
        docs = docs.filter(sender_department_id=sender_dept)

    if start_date:
        docs = docs.filter(date_received__gte=start_date)

    if end_date:
        docs = docs.filter(date_received__lte=end_date)

    #  EXPORT CSV
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="report.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Doc No", "Subject", "Type", "Sender", "Date", "Status"
        ])

        for d in docs:
            writer.writerow([
                d.doc_number,
                d.subject,
                d.doc_type_other if d.doc_type == "other" else d.get_doc_type_display(),
                d.sender_department.name if d.sender_department else d.sender_other,
                d.date_received,
                d.status
            ])

        return response

    return render(request, "report.html", {
        "documents": docs,
        "departments": Department.objects.all()
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Count, Q
from .models import Document

@login_required
def master_dashboard(request):

    query = request.GET.get("q")
    user_id = request.GET.get("user")
    show_all = request.GET.get("all")

    documents = Document.objects.all().select_related('current_holder')

    # 🔥 Only filter closed when NOT viewing all
    if not show_all:
        documents = documents.exclude(status__icontains="closed")

    if query:
        documents = documents.filter(
            Q(subject__icontains=query) |
            Q(doc_number__icontains=query)
        )

    if user_id:
        documents = documents.filter(current_holder_id=user_id)

    # 👥 Workload
    user_data = (
        Document.objects
        .exclude(status__icontains="closed")
        .filter(current_holder__isnull=False)
        .values(
            'current_holder__id',
            'current_holder__first_name',
            'current_holder__last_name'
        )
        .annotate(total_docs=Count('id'))
        .order_by('-total_docs')
    )

    # 📊 Stats
    total_docs = Document.objects.count()
    active_docs = Document.objects.exclude(status__icontains="closed").count()
    closed_docs = Document.objects.filter(status__icontains="closed").count()
    external_docs = Document.objects.filter(is_external=True).count()

    return render(request, 'master_dashboard.html', {
        'documents': documents,
        'user_data': user_data,
        'total_docs': total_docs,
        'active_docs': active_docs,
        'closed_docs': closed_docs,
        'external_docs': external_docs,
    })