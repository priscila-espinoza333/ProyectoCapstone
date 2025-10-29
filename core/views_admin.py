# core/views_admin.py

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

@staff_member_required
def admin_bi_dashboard(request):
    return render(request, "core/admin/bi_dashboard.html")