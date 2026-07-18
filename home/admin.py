from django.contrib import admin
from .models import Passenger, Station, LuggageBooking, Officer

admin.site.register(Passenger)
admin.site.register(Station)
admin.site.register(LuggageBooking)
admin.site.register(Officer)