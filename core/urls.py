from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_document, name='create_document'),
    path('forward/<int:doc_id>/', views.forward_page, name='forward_page'),
    path('forward/submit/<int:doc_id>/', views.forward_document_view, name='forward_document'),
    path('close/<int:doc_id>/', views.close_document, name='close_document'),
    path('document/<int:doc_id>/', views.document_detail, name='document_detail'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('external-decision/<int:doc_id>/', views.external_decision, name='external_decision'),
    path('api/tv-dashboard/', views.tv_dashboard_api, name='tv_dashboard_api'),
    path('tv-dashboard/', views.tv_dashboard_view, name='tv_dashboard'),
    path('sent-documents/', views.sent_documents, name='sent_documents'),
    path('receive-back/<int:doc_id>/', views.receive_back, name='receive_back'),
    path('receive-mark/<int:doc_id>/', views.receive_and_mark, name='receive_and_mark'),
    path('receive-close/<int:doc_id>/', views.receive_and_close, name='receive_and_close'),
    path('report/', views.report_view, name='report'),
    path('master-dashboard/', views.master_dashboard, name='master_dashboard'),
]