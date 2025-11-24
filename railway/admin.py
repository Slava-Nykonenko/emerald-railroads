from django.contrib import admin

from railway.models import (
    Station,
    TrainType,
    Crew,
    Train,
    Route,
    Order,
    Journey,
    Ticket
)


# Register your models here.
class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1

admin.site.register(Station)
admin.site.register(TrainType)
admin.site.register(Crew)
admin.site.register(Train)
admin.site.register(Route)
admin.site.register(Order)
admin.site.register(Journey)
