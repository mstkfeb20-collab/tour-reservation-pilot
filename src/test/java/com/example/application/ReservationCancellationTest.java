package com.example.application;

import com.example.domain.CancellationAudit;
import com.example.domain.CancellationAuditRepository;
import com.example.domain.Money;
import com.example.domain.Refund;
import com.example.domain.RefundRepository;
import com.example.domain.Reservation;
import com.example.domain.ReservationRepository;
import com.example.domain.Tour;
import com.example.domain.TransferStatus;
import com.example.infrastructure.InMemoryCancellationAuditRepository;
import com.example.infrastructure.InMemoryRefundRepository;
import com.example.infrastructure.InMemoryReservationRepository;
import com.example.infrastructure.InMemoryTourRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

@Tag("REQ-22002")
@DisplayName("REQ-22002 予約取消")
class ReservationCancellationTest {

    private static final LocalDate DEPARTURE = LocalDate.of(2027, 4, 30);
    private static final LocalDate TODAY = DEPARTURE.minusDays(1);

    private InMemoryTourRepository tours;
    private InMemoryReservationRepository reservations;
    private InMemoryRefundRepository refunds;
    private InMemoryCancellationAuditRepository audit;
    private ReservationService service;

    @BeforeEach
    void setUp() {
        tours = new InMemoryTourRepository();
        tours.save(new Tour("T001", "春の京都", DEPARTURE, Money.yen(30_000), Money.yen(15_000), 10));
        reservations = new InMemoryReservationRepository();
        refunds = new InMemoryRefundRepository();
        audit = new InMemoryCancellationAuditRepository();
        service = new ReservationService(tours, reservations, refunds, audit);
    }

    @Test
    @DisplayName("未振込予約を取り消すと理由と取消日が記録され、残席が戻り返金は登録されない")
    void unpaidCancellation() {
        Reservation reservation = reserve("R1", "M001");

        ReservationService.CancelResult result = cancel("R1", "都合により取消", TODAY, "M001");

        assertEquals(Money.zero(), result.fee());
        assertEquals(Money.zero(), result.refund());
        assertEquals(TransferStatus.CANCELLED, reservation.status());
        assertEquals(TODAY, reservation.cancelDate());
        assertEquals("都合により取消", reservation.cancelReason());
        assertEquals(10, remainingSeats());
        assertEquals(0, refunds.entries().size());
        assertEquals(1, audit.entries().size());
        assertEquals("M001", audit.entries().get(0).operator());
    }

    @Test
    @DisplayName("振込済予約は入金額から取消料を引いた返金待ちを1件登録する")
    void paidCancellationCreatesRefund() {
        Reservation reservation = reserve("R1", "M001");
        service.recordPayment("R1", DEPARTURE.minusDays(30), Money.yen(60_000));

        ReservationService.CancelResult result = cancel("R1", "予定変更", TODAY, "M001");

        assertEquals(Money.yen(30_000), result.fee());
        assertEquals(Money.yen(30_000), result.refund());
        assertEquals(1, refunds.entries().size());
        assertEquals("R1", refunds.entries().get(0).reserveNo());
        assertEquals(Money.yen(30_000), refunds.entries().get(0).refundAmount());
        assertEquals(Money.yen(30_000), refunds.entries().get(0).cancelFee());
        assertEquals(com.example.domain.RefundStatus.WAITING, refunds.entries().get(0).status());
        assertEquals("M001", refunds.entries().get(0).createdBy());
        assertEquals(10, remainingSeats());
        assertEquals(TransferStatus.CANCELLED, reservation.status());
        assertEquals(Money.yen(30_000), audit.entries().get(0).fee());
        assertEquals(Money.yen(30_000), audit.entries().get(0).refund());
    }

    @Test
    @DisplayName("返金待ち登録に失敗したら予約と残席を取り消し前に戻す")
    void rollsBackWhenRefundRegistrationFails() {
        Reservation reservation = reserve("R1", "M001");
        service.recordPayment("R1");
        RefundRepository failingRefunds = new RefundRepository() {
            @Override
            public Refund register(
                String reserveNo,
                LocalDate cancelDate,
                Money refundAmount,
                Money cancelFee,
                String operator
            ) {
                throw new IllegalStateException("返金待ちを登録できません");
            }

            @Override
            public void rollbackRegistration(String reserveNo) {
            }
        };
        service = new ReservationService(tours, reservations, failingRefunds, audit);

        assertThrows(
            IllegalStateException.class,
            () -> cancel("R1", "取消理由", TODAY, "M001")
        );

        assertEquals(TransferStatus.PAID, reservation.status());
        assertEquals(7, remainingSeats());
        assertEquals(0, audit.entries().size());
    }

    @Test
    @DisplayName("操作ログに失敗したら返金待ち・予約・残席を取り消し前に戻す")
    void rollsBackWhenAuditRecordingFails() {
        Reservation reservation = reserve("R1", "M001");
        service.recordPayment("R1");
        CancellationAuditRepository failingAudit = new CancellationAuditRepository() {
            @Override
            public void record(CancellationAudit entry) {
                throw new IllegalStateException("操作ログを記録できません");
            }

            @Override
            public void remove(CancellationAudit entry) {
            }
        };
        service = new ReservationService(tours, reservations, refunds, failingAudit);

        assertThrows(
            IllegalStateException.class,
            () -> cancel("R1", "取消理由", TODAY, "M001")
        );

        assertEquals(TransferStatus.PAID, reservation.status());
        assertEquals(7, remainingSeats());
        assertEquals(0, refunds.entries().size());
    }

    @Test
    @DisplayName("返金額は0円を下回らない")
    void refundIsNeverNegative() {
        reserve("R1", "M001");
        service.recordPayment("R1", DEPARTURE.minusDays(30), Money.yen(10_000));

        ReservationService.CancelResult result = cancel("R1", "予定変更", TODAY, "M001");

        assertEquals(Money.zero(), result.refund());
        assertEquals(Money.zero(), refunds.entries().get(0).refundAmount());
    }

    @Test
    @DisplayName("期限後入金の振込済予約も返金待ちに登録する")
    void latePaymentIsRefunded() {
        Reservation reservation = reserve("R1", "M001");
        reservation.markPaid(reservation.version(), DEPARTURE.minusDays(20), Money.yen(75_000), true);

        cancel("R1", "予定変更", DEPARTURE.minusDays(1), "M001");

        assertEquals(1, refunds.entries().size());
        assertEquals(Money.yen(45_000), refunds.entries().get(0).refundAmount());
    }

    @Test
    @DisplayName("会員は自分の予約だけ取り消せ、窓口担当は他の会員の予約も取り消せる")
    void authorization() {
        Reservation own = reserve("R1", "M001");
        Reservation another = reserve("R2", "M002");

        assertThrows(IllegalStateException.class, () -> cancel("R1", "取消理由", TODAY, "M002"));
        assertEquals(TransferStatus.UNPAID, own.status());
        cancel("R1", "取消理由", TODAY, "M001");
        cancelAsStaff("R2");

        assertEquals(TransferStatus.CANCELLED, own.status());
        assertEquals(TransferStatus.CANCELLED, another.status());
    }

    @Test
    @DisplayName("出発日当日は取り消せない")
    void departureDayIsRejected() {
        Reservation reservation = reserve("R1", "M001");

        IllegalStateException error = assertThrows(
            IllegalStateException.class,
            () -> cancel("R1", "取消理由", DEPARTURE, "M001")
        );

        assertEquals("取消期限を過ぎています", error.getMessage());
        assertEquals(TransferStatus.UNPAID, reservation.status());
        assertEquals(7, remainingSeats());
    }

    @Test
    @DisplayName("取消済み予約は再度取り消せず残席・返金待ちは変わらない")
    void alreadyCancelledIsRejectedWithoutSideEffects() {
        reserve("R1", "M001");
        cancel("R1", "取消理由", TODAY, "M001");

        IllegalStateException error = assertThrows(
            IllegalStateException.class,
            () -> cancel("R1", "再取消", TODAY, "M001")
        );

        assertEquals("この予約はすでに取り消されています", error.getMessage());
        assertEquals(10, remainingSeats());
        assertEquals(0, refunds.entries().size());
        assertEquals(1, audit.entries().size());
    }

    @Test
    @DisplayName("同じ予約を同時に取り消しても後の処理は拒否される")
    void simultaneousCancellationDoesNotRestoreSeatsTwice() throws Exception {
        reserve("R1", "M001");
        CountDownLatch ready = new CountDownLatch(2);
        CountDownLatch start = new CountDownLatch(1);
        ExecutorService executor = Executors.newFixedThreadPool(2);
        try {
            Future<Boolean> first = executor.submit(() -> tryCancel(ready, start));
            Future<Boolean> second = executor.submit(() -> tryCancel(ready, start));
            ready.await();
            start.countDown();

            assertEquals(1, (first.get() ? 1 : 0) + (second.get() ? 1 : 0));
        } finally {
            executor.shutdownNow();
        }

        assertEquals(10, remainingSeats());
        assertEquals(1, audit.entries().size());
        assertEquals(0, refunds.entries().size());
    }

    @Test
    @DisplayName("返金番号は取消日の連番で採番する")
    void refundNumbersUseDailySequence() {
        reserve("R1", "M001");
        reserve("R2", "M002");
        service.recordPayment("R1");
        service.recordPayment("R2");

        cancel("R1", "取消理由", TODAY, "M001");
        cancel("R2", "取消理由", TODAY, "M002");

        assertEquals(
            Set.of("F202704290001", "F202704290002"),
            refunds.entries().stream().map(refund -> refund.refundNo()).collect(java.util.stream.Collectors.toSet())
        );
    }

    @Test
    @DisplayName("J110との版番号競合後に振込済として読み直して1回だけ再試行する")
    void retriesAfterJ110PaymentWinsVersionConflict() {
        Reservation reservation = reserve("R1", "M001");
        ReservationRepository racingReservations = new ReservationRepository() {
            private int attempts;

            @Override
            public Optional<Reservation> findByReserveNo(String reserveNo) {
                return reservations.findByReserveNo(reserveNo);
            }

            @Override
            public void save(Reservation value) {
                reservations.save(value);
            }

            @Override
            public boolean saveCancellation(
                Reservation value,
                long expectedVersion,
                LocalDate cancelDate,
                String cancelReason,
                Runnable saveRelatedRecords
            ) {
                if (attempts++ == 0) {
                    value.markPaid(expectedVersion, DEPARTURE.minusDays(20), Money.yen(75_000), false);
                }
                return ReservationRepository.super.saveCancellation(
                    value,
                    expectedVersion,
                    cancelDate,
                    cancelReason,
                    saveRelatedRecords
                );
            }
        };
        service = new ReservationService(tours, racingReservations, refunds, audit);

        ReservationService.CancelResult result = cancel("R1", "取消理由", TODAY, "M001");

        assertEquals(Money.yen(45_000), result.refund());
        assertEquals(1, refunds.entries().size());
        assertEquals(1, audit.entries().size());
        assertEquals(10, remainingSeats());
        assertEquals(TransferStatus.CANCELLED, reservation.status());
    }

    @Test
    @DisplayName("取消料の1円未満を切り捨てる")
    void cancellationFeeRoundsDown() {
        tours.save(new Tour("T002", "料金端数", DEPARTURE, Money.yen(10_003), Money.zero(), 3));
        service.reserve("R2", "T002", "M001", 1, 0, "", DEPARTURE.minusDays(30));
        service.recordPayment("R2");

        ReservationService.CancelResult result = cancel("R2", "取消理由", DEPARTURE.minusDays(20), "M001");

        assertEquals(Money.yen(2_000), result.fee());
    }

    @Test
    @DisplayName("取消料率の境界は21・20・8・7・2・1日前で切り替わり、0日前は取消不可")
    void cancellationRateBoundaries() {
        reserve("R1", "M001");
        service.recordPayment("R1");
        assertEquals(Money.zero(), cancel("R1", "取消理由", DEPARTURE.minusDays(21), "M001").fee());

        for (int days : new int[] {20, 8, 7, 2, 1}) {
            setUp();
            reserve("R1", "M001");
            service.recordPayment("R1");
            Money expectedFee = Money.yen(75_000).percent(days >= 8 ? 20 : days >= 2 ? 30 : 40);
            assertEquals(expectedFee, cancel("R1", "取消理由", DEPARTURE.minusDays(days), "M001").fee());
        }

        setUp();
        reserve("R1", "M001");
        IllegalStateException error = assertThrows(
            IllegalStateException.class,
            () -> cancel("R1", "取消理由", DEPARTURE, "M001")
        );
        assertEquals("取消期限を過ぎています", error.getMessage());
    }

    private Reservation reserve(String reserveNo, String memberNo) {
        return service.reserve(reserveNo, "T001", memberNo, 2, 1, "", DEPARTURE.minusDays(30));
    }

    private ReservationService.CancelResult cancel(String reserveNo, String reason, LocalDate date, String memberNo) {
        return service.cancel(reserveNo, reason, date, ReservationService.CancellationActor.customer(memberNo));
    }

    private void cancelAsStaff(String reserveNo) {
        service.cancel(
            reserveNo,
            "電話受付",
            TODAY,
            ReservationService.CancellationActor.counterStaff("E001")
        );
    }

    private boolean tryCancel(CountDownLatch ready, CountDownLatch start) throws InterruptedException {
        ready.countDown();
        start.await();
        try {
            cancel("R1", "同時取消", TODAY, "M001");
            return true;
        } catch (IllegalStateException exception) {
            return false;
        }
    }

    private int remainingSeats() {
        return tours.findByCode("T001").orElseThrow().remainingSeats();
    }
}
