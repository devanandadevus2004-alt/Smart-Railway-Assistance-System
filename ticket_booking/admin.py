from django.contrib import admin
from .models import Train, Coach, Seat, TicketBooking,Payment


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = (
        'train_number',
        'train_name',
        'source_station',
        'destination_station',
        'departure_time',
        'arrival_time',
        'is_active',
    )

    search_fields = (
        'train_number',
        'train_name',
    )


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = (
        'train',
        'coach_number',
        'coach_type',
        'total_seats',
        'is_bookable',
        'has_seat_layout',
    )

    list_filter = (
        'coach_type',
        'is_bookable',
        'has_seat_layout',
    )

    search_fields = (
        'coach_number',
        'train__train_number',
    )


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = (
        'coach',
        'seat_number',
        'seat_type',
        'row_number',
        'position',
        'is_active',
    )

    list_filter = (
        'seat_type',
        'is_active',
    )

    search_fields = (
        'coach__coach_number',
    )


@admin.register(TicketBooking)
class TicketBookingAdmin(admin.ModelAdmin):
    list_display = (
        'passenger',
        'train',
        'seat',
        'travel_date',
        'booking_date',
        'status',
    )

    list_filter = (
        'status',
        'travel_date',
    )

    search_fields = (
        'passenger__full_name',
        'train__train_number',
        'train__train_name',
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'booking',
        'amount',
        'payment_method',
        'payment_status',
        'transaction_id',
        'paid_at',
    )

    list_filter = (
        'payment_status',
        'payment_method',
    )

    search_fields = (
        'booking__passenger__full_name',
        'booking__train__train_number',
        'transaction_id',
    )

