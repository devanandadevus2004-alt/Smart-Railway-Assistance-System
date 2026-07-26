from django.shortcuts import render
from home.models import Station
from .models import Train


def ticket_booking(request):

    stations = Station.objects.all().order_by('station_name')

    trains = None

    if request.method == 'POST':

        source_id = request.POST.get('source_station')
        destination_id = request.POST.get('destination_station')
        travel_date = request.POST.get('travel_date')

        trains = Train.objects.filter(
            source_station_id=source_id,
            destination_station_id=destination_id,
            is_active=True
        )

    return render(
        request,
        'ticket_booking/ticket_booking.html',
        {
            'stations': stations,
            'trains': trains,
        }
    )