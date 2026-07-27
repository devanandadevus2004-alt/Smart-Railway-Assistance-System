from django.shortcuts import render
from home.models import Station
from .models import Train, TrainStop


def ticket_booking(request):

    stations = Station.objects.all().order_by('station_name')

    trains = None
    travel_date = None

    if request.method == 'POST':

        source_id = request.POST.get('source_station')
        destination_id = request.POST.get('destination_station')
        travel_date = request.POST.get('travel_date')

        if source_id and destination_id:

            # Get all train stops for the selected source station
            source_stops = TrainStop.objects.filter(
                station_id=source_id
            )

            # Get all train stops for the selected destination station
            destination_stops = TrainStop.objects.filter(
                station_id=destination_id
            )

            # Store destination stop order by train
            destination_orders = {}

            for stop in destination_stops:
                destination_orders[stop.train_id] = stop.stop_order

            # Find trains where source comes before destination
            valid_train_ids = []

            for source_stop in source_stops:

                destination_order = destination_orders.get(
                    source_stop.train_id
                )

                if destination_order is not None:

                    if source_stop.stop_order < destination_order:
                        valid_train_ids.append(
                            source_stop.train_id
                        )

            # Get the actual Train objects
            trains = Train.objects.filter(
                id__in=valid_train_ids,
                is_active=True
            )

    return render(
        request,
        'ticket_booking/ticket_booking.html',
        {
            'stations': stations,
            'trains': trains,
            'travel_date': travel_date,
        }
    )