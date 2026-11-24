package com.example.application;

import com.example.domain.BankTransferDetail;
import com.example.domain.BankTransferFile;
import com.example.domain.Money;
import com.example.domain.PaymentAuditRepository;
import com.example.domain.PaymentHandoffRepository;
import com.example.domain.Reservation;
import com.example.domain.ReservationRepository;
import com.example.domain.Tour;
import com.example.domain.TransferImportRecord;
import com.example.domain.TransferImportRepository;
import com.example.domain.TransferImportResultCode;
import com.example.domain.TransferStatus;
import com.example.infrastructure.InMemoryPaymentAuditRepository;
import com.example.infrastructure.InMemoryPaymentHandoffRepository;
import com.example.infrastructure.InMemoryReservationRepository;
import com.example.infrastructure.InMemoryTransferImportRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@Tag("REQ-22001")
@DisplayName("REQ-22001 振込データ取込")
class TransferImportServiceTest {

    private static final LocalDate DUE_DATE = LocalDate.of(2026, 4, 1);
    private static final LocalDate ACCOUNT_DATE = LocalDate.of(2026, 4, 1);
    private static final Tour TOUR = new Tour("T0000001", "春の京都", LocalDate.of(2027, 4, 30), Money.yen(10_000), Money.yen(8_000), 10);

    private InMemoryReservationRepository reservations;
    private InMemoryTransferImportRepository imports;
    private InMemoryPaymentHandoffRepository handoffs;
    private InMemoryPaymentAuditRepository audit;
    private TransferImportService service;

    @BeforeEach
    void setUp() {
        reservations = new InMemoryReservationRepository();
        imports = new InMemoryTransferImportRepository();
        handoffs = new InMemoryPaymentHandoffRepository();
        audit = new InMemoryPaymentAuditRepository();
        service = service(reservations, imports, handoffs, audit);
    }

    @Test
    @DisplayName("EDI情報の予約番号を振込依頼人名より優先し、予約番号のない名義では消し込まない")
    void ediTakesPriorityAndNameAloneDoesNotMatch() {
        Reservation payerReservation = reserve("R000000000001");
        Reservation ediReservation = reserve("R000000000002");

        TransferImportOutcome outcome = service.importFile(file(
            detail("000001", 10_000, payerReservation.reserveNo(), ediReservation.reserveNo(), "0"),
            detail("000002", 10_000, "ﾔﾏﾀﾞﾀﾛｳ", "", "0")
        ), "bank.dat");

        assertEquals(TransferStatus.UNPAID, payerReservation.status());
        assertEquals(TransferStatus.PAID, ediReservation.status());
        assertEquals(TransferImportResultCode.SETTLED, outcome.records().get(0).result());
        assertEquals(TransferImportResultCode.NO_RESERVATION, outcome.records().get(1).result());
        assertNull(outcome.records().get(1).reserveNo());
        assertEquals(1, outcome.handoffs().size());
        assertEquals(1, handoffs.entries().size());
        assertEquals("J110", audit.entries().get(0).operator());
    }

    @Test
    @DisplayName("振込依頼人名に予約番号がなくEDI情報にある場合はEDI情報から照合する")
    void ediOnlyMatches() {
        Reservation reservation = reserve("R000000000001");

        TransferImportOutcome outcome = service.importFile(file(
            detail("000001", 10_000, "ﾔﾏﾀﾞﾀﾛｳ", reservation.reserveNo(), "0")
        ), "bank.dat");

        assertEquals(TransferImportResultCode.SETTLED, outcome.records().get(0).result());
        assertEquals(reservation.reserveNo(), outcome.records().get(0).reserveNo());
    }

    @Test
    @DisplayName("振込依頼人名だけに予約番号がある場合は依頼人名から照合する")
    void payerNameOnlyMatches() {
        Reservation reservation = reserve("R000000000001");

        TransferImportOutcome outcome = service.importFile(file(
            detail("000001", 10_000, reservation.reserveNo(), "", "0")
        ), "bank.dat");

        assertEquals(TransferImportResultCode.SETTLED, outcome.records().get(0).result());
        assertEquals(reservation.reserveNo(), outcome.records().get(0).reserveNo());
        assertEquals(TransferStatus.PAID, reservation.status());
    }

    @Test
    @DisplayName("一致・1円不足・1円超過を区別して、不足と超過では振込済にしない")
    void amountBoundaries() {
        Reservation exact = reserve("R000000000001");
        Reservation under = reserve("R000000000002");
        Reservation over = reserve("R000000000003");

        TransferImportOutcome outcome = service.importFile(file(
            detail("000001", 10_000, exact.reserveNo(), "", "0"),
            detail("000002", 9_999, under.reserveNo(), "", "0"),
            detail("000003", 10_001, over.reserveNo(), "", "0")
        ), "bank.dat");

        assertEquals(List.of(
            TransferImportResultCode.SETTLED,
            TransferImportResultCode.UNDERPAID,
            TransferImportResultCode.OVERPAID
        ), outcome.records().stream().map(TransferImportRecord::result).toList());
        assertEquals(TransferStatus.PAID, exact.status());
        assertEquals(TransferStatus.UNPAID, under.status());
        assertEquals(TransferStatus.UNPAID, over.status());
    }

    @Test
    @DisplayName("振込済・取消済の予約は返金対象、組戻しは要確認になる")
    void paidCancelledAndReversal() {
        Reservation paid = reserve("R000000000001");
        paid.markPaid();
        Reservation cancelled = reserve("R000000000002");
        cancelled.cancel(ACCOUNT_DATE, "取消");

        TransferImportOutcome outcome = service.importFile(file(
            detail("000001", 10_000, paid.reserveNo(), "", "0"),
            detail("000002", 10_000, cancelled.reserveNo(), "", "0"),
            detail("000003", 10_000, "R000000000003", "", "1")
        ), "bank.dat");

        assertEquals(List.of(
            TransferImportResultCode.DUPLICATE_PAYMENT,
            TransferImportResultCode.PAID_AFTER_CANCELLATION,
            TransferImportResultCode.REVERSAL
        ), outcome.records().stream().map(TransferImportRecord::result).toList());
        assertEquals("40", outcome.records().get(2).result().code());
        assertEquals(Money.yen(10_000), outcome.records().get(0).amount());
        assertEquals(Money.yen(10_000), outcome.records().get(1).amount());
        assertEquals(0, outcome.handoffs().size());
    }

    @Test
    @DisplayName("同一予約への2明細は照会番号の小さい方だけを消し込む")
    void lowestInquirySettles() {
        Reservation reservation = reserve("R000000000001");

        TransferImportOutcome outcome = service.importFile(file(
            detail("000002", 10_000, reservation.reserveNo(), "", "0"),
            detail("000001", 10_000, reservation.reserveNo(), "", "0")
        ), "bank.dat");

        assertEquals(TransferImportResultCode.SETTLED, outcome.records().get(0).result());
        assertEquals("000001", outcome.records().get(0).inquiryNo());
        assertEquals(TransferImportResultCode.DUPLICATE_PAYMENT, outcome.records().get(1).result());
        assertEquals(1, outcome.handoffs().size());
    }

    @Test
    @DisplayName("勘定日が振込期限当日なら期限内、翌日なら期限後として記録する")
    void dueDateBoundary() {
        Reservation dueDate = reserve("R000000000001");
        Reservation afterDueDate = reserve("R000000000002");
        BankTransferFile file = new BankTransferFile(
            LocalDate.of(2026, 4, 1),
            "1234567",
            List.of(detail("000001", 10_000, dueDate.reserveNo(), "", "0"),
                new BankTransferDetail("000002", ACCOUNT_DATE.plusDays(1), ACCOUNT_DATE.plusDays(1), Money.yen(10_000),
                    afterDueDate.reserveNo(), "0", "")),
            Money.yen(20_000)
        );

        service.importFile(file, "bank.dat");

        assertFalse(dueDate.latePayment());
        assertEquals(ACCOUNT_DATE, dueDate.paidDate());
        assertTrue(afterDueDate.latePayment());
        assertEquals(Money.yen(10_000), afterDueDate.paidAmount());
    }

    @Test
    @DisplayName("予約取消との版番号競合は要確認として保存する")
    void versionConflictNeedsReview() {
        Reservation reservation = reserve("R000000000001");
        TransferImportRepository racingImports = new TransferImportRepository() {
            @Override
            public Optional<TransferImportRecord> findByAccountDateAndInquiryNo(LocalDate date, String inquiryNo) {
                return imports.findByAccountDateAndInquiryNo(date, inquiryNo);
            }

            @Override
            public void save(TransferImportRecord record) {
                imports.save(record);
            }

            @Override
            public boolean saveSettlement(Reservation value, long expectedVersion, boolean latePayment, TransferImportRecord record) {
                reservation.cancel(ACCOUNT_DATE, "取消");
                return false;
            }

            @Override
            public boolean hasImportedFile(LocalDate date, int count, Money amount) {
                return imports.hasImportedFile(date, count, amount);
            }

            @Override
            public void saveFileSummary(LocalDate date, int count, Money amount) {
                imports.saveFileSummary(date, count, amount);
            }
        };
        TransferImportService racingService = service(reservations, racingImports, handoffs, audit);

        TransferImportOutcome outcome = racingService.importFile(file(
            detail("000001", 10_000, reservation.reserveNo(), "", "0")
        ), "bank.dat");

        assertEquals(TransferImportResultCode.REVIEW, outcome.records().get(0).result());
        assertEquals("41", outcome.records().get(0).result().code());
        assertEquals(TransferStatus.CANCELLED, reservation.status());
    }

    @Test
    @DisplayName("途中終了後の再実行は保存済み明細を読み飛ばして残りを処理する")
    void resumesAfterCommittedDetail() {
        Reservation first = reserve("R000000000001");
        Reservation second = reserve("R000000000002");
        TransferImportRepository failsOnce = new TransferImportRepository() {
            private int lookupCount;
            private boolean failed;

            @Override
            public Optional<TransferImportRecord> findByAccountDateAndInquiryNo(LocalDate date, String inquiryNo) {
                if (++lookupCount == 2 && !failed) {
                    failed = true;
                    throw new IllegalStateException("simulated stop");
                }
                return imports.findByAccountDateAndInquiryNo(date, inquiryNo);
            }

            @Override
            public void save(TransferImportRecord record) {
                imports.save(record);
            }

            @Override
            public boolean saveSettlement(Reservation reservation, long expectedVersion, boolean latePayment, TransferImportRecord record) {
                return imports.saveSettlement(reservation, expectedVersion, latePayment, record);
            }

            @Override
            public boolean hasImportedFile(LocalDate date, int count, Money amount) {
                return imports.hasImportedFile(date, count, amount);
            }

            @Override
            public void saveFileSummary(LocalDate date, int count, Money amount) {
                imports.saveFileSummary(date, count, amount);
            }
        };
        TransferImportService restartable = service(reservations, failsOnce, handoffs, audit);
        BankTransferFile file = file(
            detail("000001", 10_000, first.reserveNo(), "", "0"),
            detail("000002", 10_000, second.reserveNo(), "", "0")
        );

        try {
            restartable.importFile(file, "bank.dat");
        } catch (IllegalStateException expected) {
            assertEquals(TransferStatus.PAID, first.status());
            assertEquals(TransferStatus.UNPAID, second.status());
        }
        TransferImportOutcome outcome = restartable.importFile(file, "bank.dat");

        assertEquals(2, outcome.records().size());
        assertEquals(TransferStatus.PAID, second.status());
        assertEquals(2, imports.findByAccountDateAndInquiryNo(ACCOUNT_DATE, "000001").stream().count()
            + imports.findByAccountDateAndInquiryNo(ACCOUNT_DATE, "000002").stream().count());
    }

    private Reservation reserve(String reserveNo) {
        Reservation reservation = Reservation.create(reserveNo, TOUR, 1, 0, "", DUE_DATE);
        reservations.save(reservation);
        return reservation;
    }

    private static BankTransferDetail detail(String inquiryNo, long amount, String payerName, String edi, String cancellation) {
        return new BankTransferDetail(inquiryNo, ACCOUNT_DATE, ACCOUNT_DATE, Money.yen(amount), payerName, cancellation, edi);
    }

    private static BankTransferFile file(BankTransferDetail... details) {
        return new BankTransferFile(
            LocalDate.of(2026, 4, 1),
            "1234567",
            List.of(details),
            Money.yen(List.of(details).stream().mapToLong(detail -> detail.amount().toLong()).sum())
        );
    }

    private static TransferImportService service(
        ReservationRepository reservations,
        TransferImportRepository imports,
        PaymentHandoffRepository handoffs,
        PaymentAuditRepository audit
    ) {
        return new TransferImportService(reservations, imports, handoffs, audit);
    }
}
