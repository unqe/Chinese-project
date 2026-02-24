"""Quick admin debug script — run with: heroku run python admin_debug.py"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'despair.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from orders.admin import OrderAdmin
from orders.models import Order
import traceback

admin_user = User.objects.filter(is_superuser=True).first()
print("Admin user:", admin_user)

factory = RequestFactory()
site = AdminSite()
oa = OrderAdmin(Order, site)
o = Order.objects.first()
print("Order pk:", o.pk if o else None)

# Test changelist (list view)
print("\n-- changelist_view --")
try:
    request = factory.get('/admin/orders/order/')
    request.user = admin_user
    response = oa.changelist_view(request)
    print("OK status:", response.status_code)
except Exception as e:
    traceback.print_exc()

# Test change form (detail view)
print("\n-- changeform_view (existing) --")
try:
    request = factory.get(f'/admin/orders/order/{o.pk}/change/')
    request.user = admin_user
    response = oa.changeform_view(request, str(o.pk))
    print("OK status:", response.status_code)
except Exception as e:
    traceback.print_exc()

# Test add form
print("\n-- changeform_view (add) --")
try:
    request = factory.get('/admin/orders/order/add/')
    request.user = admin_user
    response = oa.changeform_view(request, None)
    print("OK status:", response.status_code)
except Exception as e:
    traceback.print_exc()

print("\nDone.")
