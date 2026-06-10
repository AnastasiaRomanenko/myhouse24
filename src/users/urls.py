from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from src.authentication.forms import CustomSetPasswordForm
from src.users.views import owners, roles, users

Users = get_user_model()
app_name = "users"

urlpatterns = [
    path("owners/", owners.OwnersListView.as_view(), name="owner_list"),
    path(
        "owners/ajax",
        owners.OwnersAjaxDatatableView.as_view(),
        name="owner_ajax_list",
    ),
    path(
        "owner/create/", owners.OwnerCreateView.as_view(), name="owner_create"
    ),
    path(
        "owners/<int:pk>/profile/",
        owners.OwnerProfileView.as_view(),
        name="owner_profile",
    ),
    path(
        "owners/<int:pk>/update/",
        owners.OwnerUpdateView.as_view(),
        name="owner_update",
    ),
    path(
        "owners/<int:pk>/delete/",
        owners.OwnerDeleteView.as_view(),
        name="owner_delete",
    ),
    path(
        "owners/invitation",
        owners.OwnerInviteView.as_view(),
        name="owner_invite",
    ),
    path(
        "ajax/owners/select2/",
        owners.OwnerSelect2View.as_view(),
        name="owner_select2",
    ),
    # path("owners/<int:pk>/message/", owners.OwnerMessageView.as_view(), name="owner_message"),
    path("roles/", roles.RolesListView.as_view(), name="roles_list"),
    path(
        "roles/ajax",
        roles.RolesAjaxDatatableView.as_view(),
        name="roles_ajax_list",
    ),
    path("admins/", users.UsersListView.as_view(), name="admin_list"),
    path(
        "admins/ajax",
        users.UsersAjaxDatatableView.as_view(),
        name="admin_ajax_list",
    ),
    path(
        "admins/create/", users.UserCreateView.as_view(), name="admin_create"
    ),
    path(
        "admins/<int:pk>/profile/",
        users.UserProfileView.as_view(),
        name="admin_profile",
    ),
    path(
        "admins/<int:pk>/update/",
        users.UserUpdateView.as_view(),
        name="admin_update",
    ),
    path(
        "admins/<int:pk>/delete/",
        users.UserDeleteView.as_view(),
        name="admin_delete",
    ),
    path(
        "admins/<int:pk>/invite/",
        users.UserInviteView.as_view(),
        name="admin_invite",
    ),
    path(
        "set_password/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=CustomSetPasswordForm,
            template_name="users/set_password.html",
            success_url=reverse_lazy("users:invitation_complete"),
        ),
        name="set_password",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="users/invitation_complete.html"
        ),
        name="invitation_complete",
    ),
]
