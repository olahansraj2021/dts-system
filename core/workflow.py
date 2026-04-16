from django.contrib.auth.models import User
from .models import Movement


# Get users by role (AR, JAA, etc.)
def get_users_by_role(role):
    return User.objects.filter(profile__role=role)


#  Get next role users (optional use)
def get_next_role_users(current_user):
    role_flow = ["dispatch", "dr", "ar", "as", "jaa"]

    current_role = current_user.profile.role

    if current_role in role_flow:
        index = role_flow.index(current_role)

        if index + 1 < len(role_flow):
            next_role = role_flow[index + 1]
            return get_users_by_role(next_role)

    return []


#  FORWARD FUNCTION (MAIN LOGIC)
def forward_document(document, from_user, to_user, remarks=""):

    if not to_user:
        raise ValueError("Next user required")

    # Save movement history
    Movement.objects.create(
        document=document,
        from_user=from_user,
        to_user=to_user,
        action="forward",
        remarks=remarks
    )

    # Update document
    document.current_holder = to_user
    document.status = "Pending"
    document.save()

    return document


#  RETURN FUNCTION (AUTO PREVIOUS USER)
def return_document(document, user, remarks=""):

    # Get last movement
    last_movement = Movement.objects.filter(document=document).order_by('-id').first()

    if not last_movement:
        raise ValueError("No previous movement found")

    previous_user = last_movement.from_user

    # Save return movement
    Movement.objects.create(
        document=document,
        from_user=user,
        to_user=previous_user,
        action="return",
        remarks=remarks
    )

    # Update document
    document.current_holder = previous_user
    document.status = "Returned"
    document.save()

    return document


#  APPROVE FUNCTION
def approve_document(document, user, remarks=""):

    Movement.objects.create(
        document=document,
        from_user=user,
        to_user=user,
        action="approved",
        remarks=remarks
    )

    document.status = "Approved"
    document.save()

    return document


#  REJECT FUNCTION
def reject_document(document, user, remarks=""):

    Movement.objects.create(
        document=document,
        from_user=user,
        to_user=user,
        action="rejected",
        remarks=remarks
    )

    document.status = "Rejected"
    document.save()

    return document