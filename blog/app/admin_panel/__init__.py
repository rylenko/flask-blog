from flask_admin import AdminIndexView as BaseAdminIndexView

from .base import AdminRequiredMixin


class AdminIndexView(AdminRequiredMixin, BaseAdminIndexView):
	pass
