package com.example.application;

import com.example.domain.CancellationPolicy;
import com.example.domain.Money;
import com.example.domain.Reservation;
import com.example.domain.ReservationRepository;
import com.example.domain.Tour;
import com.example.domain.TourRepository;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;

/** ツアー予約のユースケース。domain だけに依存する。日付はテストできるよう引数で受け取る。 */
public class ReservationService {

    /** 予約は出発日の7日前まで（REQ-001）。 */
    static final int RESERVE_DEADLINE_DAYS = 7;

    private final TourRepository tours;
    private final ReservationRepository reservations;

    public ReservationService(TourRepository tours, ReservationRepository reservations) {
        this.tours = tours;
        this.reservations = reservations;
    }

    /** 予約する（REQ-001）。予約の登録と残席の減算はまとめて行う。 */
    public Reservation reserve(String reserveNo, String tourCode, int adultCount, int childCount, String remarks, LocalDate today) {
        Tour tour = findTour(tourCode);
        if (ChronoUnit.DAYS.between(today, tour.departureDate()) < RESERVE_DEADLINE_DAYS) {
            throw new IllegalStateException("ご予約は出発日の" + RESERVE_DEADLINE_DAYS + "日前までです");
        }
        Reservation reservation = Reservation.create(reserveNo, tour, adultCount, childCount, remarks);
        tour.reserveSeats(reservation.headcount());
        reservations.save(reservation);
        tours.save(tour);
        return reservation;
    }

    /** 振込を記録する。 */
    public Reservation recordPayment(String reserveNo) {
        Reservation reservation = findReservation(reserveNo);
        reservation.markPaid();
        reservations.save(reservation);
        return reservation;
    }

    /** 取り消す（REQ-002, REQ-003）。状態の更新と残席の戻しはまとめて行う。 */
    public CancelResult cancel(String reserveNo, LocalDate today) {
        Reservation reservation = findReservation(reserveNo);
        Tour tour = findTour(reservation.tourCode());
        long days = ChronoUnit.DAYS.between(today, tour.departureDate());
        if (!CancellationPolicy.canCancel(days)) {
            throw new IllegalStateException("取消期限を過ぎています");
        }
        Money fee = CancellationPolicy.fee(reservation, days);
        Money refund = CancellationPolicy.refund(reservation, days);
        reservation.cancel();
        tour.releaseSeats(reservation.headcount());
        reservations.save(reservation);
        tours.save(tour);
        return new CancelResult(fee, refund);
    }

    private Tour findTour(String code) {
        return tours.findByCode(code)
            .orElseThrow(() -> new IllegalArgumentException("ツアーが見つかりません: " + code));
    }

    private Reservation findReservation(String reserveNo) {
        return reservations.findByReserveNo(reserveNo)
            .orElseThrow(() -> new IllegalArgumentException("この予約は取り消せません: " + reserveNo));
    }

    /** 取消の結果。取消料と返金額。 */
    public record CancelResult(Money fee, Money refund) {
    }
}
