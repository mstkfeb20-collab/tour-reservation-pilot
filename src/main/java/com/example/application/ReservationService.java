package com.example.application;

import com.example.domain.CancellationAudit;
import com.example.domain.CancellationAuditRepository;
import com.example.domain.CancellationPolicy;
import com.example.domain.Money;
import com.example.domain.Reservation;
import com.example.domain.ReservationRepository;
import com.example.domain.RefundRepository;
import com.example.domain.Tour;
import com.example.domain.TourRepository;
import com.example.domain.TransferStatus;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.Objects;

/** ツアー予約のユースケース。domain だけに依存する。日付はテストできるよう引数で受け取る。 */
public class ReservationService {

    /** 予約は出発日の7日前まで（REQ-001）。 */
    static final int RESERVE_DEADLINE_DAYS = 7;

    private final TourRepository tours;
    private final ReservationRepository reservations;
    private final RefundRepository refunds;
    private final CancellationAuditRepository cancellationAudit;

    public ReservationService(
        TourRepository tours,
        ReservationRepository reservations,
        RefundRepository refunds,
        CancellationAuditRepository cancellationAudit
    ) {
        this.tours = tours;
        this.reservations = reservations;
        this.refunds = refunds;
        this.cancellationAudit = cancellationAudit;
    }

    /** 予約する（REQ-001）。予約の登録と残席の減算はまとめて行う。 */
    public Reservation reserve(String reserveNo, String tourCode, int adultCount, int childCount, String remarks, LocalDate today) {
        return reserve(reserveNo, tourCode, adultCount, childCount, remarks, today, null);
    }

    public Reservation reserve(
        String reserveNo,
        String tourCode,
        String memberNo,
        int adultCount,
        int childCount,
        String remarks,
        LocalDate today
    ) {
        Tour tour = findTour(tourCode);
        if (ChronoUnit.DAYS.between(today, tour.departureDate()) < RESERVE_DEADLINE_DAYS) {
            throw new IllegalStateException("ご予約は出発日の" + RESERVE_DEADLINE_DAYS + "日前までです");
        }
        Reservation reservation = Reservation.create(reserveNo, tour, memberNo, adultCount, childCount, remarks, null);
        synchronized (tour) {
            tour.reserveSeats(reservation.headcount());
            reservations.save(reservation);
            tours.save(tour);
        }
        return reservation;
    }

    public Reservation reserve(
        String reserveNo,
        String tourCode,
        int adultCount,
        int childCount,
        String remarks,
        LocalDate today,
        LocalDate payDueDate
    ) {
        Tour tour = findTour(tourCode);
        if (ChronoUnit.DAYS.between(today, tour.departureDate()) < RESERVE_DEADLINE_DAYS) {
            throw new IllegalStateException("ご予約は出発日の" + RESERVE_DEADLINE_DAYS + "日前までです");
        }
        Reservation reservation = Reservation.create(reserveNo, tour, adultCount, childCount, remarks, payDueDate);
        synchronized (tour) {
            tour.reserveSeats(reservation.headcount());
            reservations.save(reservation);
            tours.save(tour);
        }
        return reservation;
    }

    /** 振込を記録する。 */
    public Reservation recordPayment(String reserveNo) {
        Reservation reservation = findReservation(reserveNo);
        reservation.markPaid();
        reservations.save(reservation);
        return reservation;
    }

    public Reservation recordPayment(String reserveNo, LocalDate date, Money amount) {
        Reservation reservation = findReservation(reserveNo);
        reservation.markPaid(reservation.version(), date, amount, false);
        reservations.save(reservation);
        return reservation;
    }

    public CancelResult cancel(String reserveNo, String cancelReason, LocalDate today, CancellationActor actor) {
        validateCancelReason(cancelReason);
        Objects.requireNonNull(today);
        Objects.requireNonNull(actor);

        for (int attempt = 0; attempt < 2; attempt++) {
            Reservation reservation = findReservation(reserveNo);
            synchronized (reservation) {
                if (actor.role() == OperatorRole.CUSTOMER && !reservation.memberNo().equals(actor.id())) {
                    throw new IllegalStateException("この予約は取り消せません");
                }
                if (reservation.status() == TransferStatus.CANCELLED) {
                    throw new IllegalStateException("この予約はすでに取り消されています");
                }

                Tour tour = findTour(reservation.tourCode());
                long days = ChronoUnit.DAYS.between(today, tour.departureDate());
                if (!CancellationPolicy.canCancel(days)) {
                    throw new IllegalStateException("取消期限を過ぎています");
                }
                Money fee = CancellationPolicy.fee(reservation, days);
                Money refund = CancellationPolicy.refund(reservation, days);
                boolean paid = reservation.status() == TransferStatus.PAID;
                long expectedVersion = reservation.version();
                synchronized (tour) {
                    if (!reservations.saveCancellation(
                        reservation,
                        expectedVersion,
                        today,
                        cancelReason,
                        () -> persistCancellationSideEffects(
                            reserveNo,
                            today,
                            reservation.headcount(),
                            paid,
                            fee,
                            refund,
                            actor.id(),
                            tour
                        )
                    )) {
                        if (attempt == 1) {
                            throw new IllegalStateException("予約を更新できませんでした");
                        }
                        continue;
                    }
                    return new CancelResult(fee, refund);
                }
            }
        }
        throw new IllegalStateException("予約を更新できませんでした");
    }

    private void persistCancellationSideEffects(
        String reserveNo,
        LocalDate cancelDate,
        int headcount,
        boolean paid,
        Money fee,
        Money refund,
        String operator,
        Tour tour
    ) {
        boolean refundRegistered = false;
        CancellationAudit auditEntry = new CancellationAudit(reserveNo, operator, fee, refund);
        try {
            tour.releaseSeats(headcount);
            tours.save(tour);
            if (paid) {
                refunds.register(reserveNo, cancelDate, refund, fee, operator);
                refundRegistered = true;
            }
            cancellationAudit.record(auditEntry);
        } catch (RuntimeException exception) {
            cancellationAudit.remove(auditEntry);
            if (refundRegistered) {
                refunds.rollbackRegistration(reserveNo);
            }
            tour.reserveSeats(headcount);
            tours.save(tour);
            throw exception;
        }
    }

    private void validateCancelReason(String cancelReason) {
        if (cancelReason == null || cancelReason.isEmpty()) {
            throw new IllegalArgumentException("取消理由を入力してください");
        }
        if (cancelReason.codePointCount(0, cancelReason.length()) > 100) {
            throw new IllegalArgumentException("取消理由は100文字以内で入力してください");
        }
    }

    private Tour findTour(String code) {
        return tours.findByCode(code)
            .orElseThrow(() -> new IllegalArgumentException("ツアーが見つかりません: " + code));
    }

    private Reservation findReservation(String reserveNo) {
        return reservations.findByReserveNo(reserveNo)
            .orElseThrow(() -> new IllegalStateException("この予約は取り消せません"));
    }

    public enum OperatorRole {
        CUSTOMER,
        COUNTER_STAFF
    }

    public record CancellationActor(String id, OperatorRole role) {
        public CancellationActor {
            if (id == null || id.isBlank() || id.length() > 10) {
                throw new IllegalArgumentException("操作した人は1〜10文字で指定してください");
            }
            Objects.requireNonNull(role);
        }

        public static CancellationActor customer(String memberNo) {
            return new CancellationActor(memberNo, OperatorRole.CUSTOMER);
        }

        public static CancellationActor counterStaff(String employeeNo) {
            return new CancellationActor(employeeNo, OperatorRole.COUNTER_STAFF);
        }
    }

    /** 取消の結果。取消料と返金額。 */
    public record CancelResult(Money fee, Money refund) {
    }
}
