"""Job management API urls"""

from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('create', views.JobCreate.as_view(), name='job_create'),
    path('<str:job_id>/results', views.JobResults.as_view(), name='job_results'),
    path('<str:job_id>/delete', views.JobDelete.as_view(), name='job_delete'),
    path('<str:job_id>/status', views.JobStatus.as_view(), name='job_status'),
    path('status/list', views.JobStatusList.as_view(), name='job_status_list'),
    path('<str:job_id>/size', views.JobSize.as_view(), name='job_size'),
]
