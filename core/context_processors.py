from .models import Document

def global_data(request):
    if request.user.is_authenticated:
        count = Document.objects.filter(current_holder=request.user).count()
    else:
        count = 0

    return {'pending_count': count}