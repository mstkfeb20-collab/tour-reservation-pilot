package com.example.application;

import com.example.domain.Money;
import com.example.domain.BankTransferDetail;
import com.example.domain.BankTransferFile;
import com.example.domain.CancellationAudit;
import com.example.domain.CancellationAuditRepository;
import com.example.domain.Tour;
import com.example.domain.TransferImportRecord;
import com.example.domain.TransferImportResultCode;
import com.example.infrastructure.InMemoryCancellationAuditRepository;
import com.example.infrastructure.InMemoryClaimRepository;
import com.example.infrastructure.InMemoryPaymentAuditRepository;
import com.example.infrastructure.InMemoryPaymentHandoffRepository;
import com.example.infrastructure.InMemoryRefundRepository;
import com.example.infrastructure.InMemoryReservationRepository;
import com.example.infrastructure.InMemoryTourRepository;
import com.example.infrastructure.InMemoryTransferImportRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;

@Tag("REQ-22002")
@DisplayName("REQ-22002 取消時の精算")
class CancellationSettlementTest {
    private static final LocalDate DEPARTURE = LocalDate.of(2027, 4, 30);
    private final InMemoryTourRepository tours = new InMemoryTourRepository();
    private final InMemoryReservationRepository reservations = new InMemoryReservationRepository();
    private final InMemoryRefundRepository refunds = new InMemoryRefundRepository();
    private final InMemoryClaimRepository claims = new InMemoryClaimRepository();
    private final InMemoryTransferImportRepository imports = new InMemoryTransferImportRepository();
    private final InMemoryCancellationAuditRepository audit = new InMemoryCancellationAuditRepository();
    private ReservationService service;

    @BeforeEach
    void setUp() {
        tours.save(new Tour("T001", "京都", DEPARTURE, Money.yen(30_000), Money.zero(), 10));
        service = new ReservationService(tours, reservations, refunds, claims, imports, audit);
        service.reserve("R1", "T001", "M001", 1, 0, "", DEPARTURE.minusDays(30));
    }

    @Test
    @Tag("S-26-002/D-15001/6")
    @DisplayName("入金なしの取消で取消料全額を請求し残席を戻す")
    void noPayment() {
        var result = cancel(DEPARTURE.minusDays(1));
        assertEquals(Money.yen(12_000), result.fee());
        assertEquals(Money.zero(), result.paid());
        assertEquals(Money.yen(12_000), result.claim());
        assertEquals(Money.yen(12_000), claims.entries().get(0).claimAmount());
        assertEquals("C202704290001", claims.entries().get(0).claimNo());
        assertEquals("0", claims.entries().get(0).status().code());
        assertEquals(Money.zero(), claims.entries().get(0).paidAmount());
        assertEquals(0, refunds.entries().size());
        assertEquals(10, tours.findByCode("T001").orElseThrow().remainingSeats());
    }

    @Test
    @Tag("S-26-002/D-15001/7")
    @Tag("S-26-002/D-15003/3")
    @DisplayName("不足明細を合算して取消料の前後1円と同額を精算する")
    void underpaymentBoundaries() {
        for (long amount : new long[] {11_999, 12_000, 12_001}) {
            if (amount != 11_999) {
                setUp();
            }
            addImport("000001", Money.yen(amount - 1), TransferImportResultCode.UNDERPAID);
            addImport("000002", Money.yen(1), TransferImportResultCode.UNDERPAID);
            var result = cancel(DEPARTURE.minusDays(1));
            assertEquals(Money.yen(amount), result.paid());
            assertEquals(Money.yen(Math.max(0, amount - 12_000)), result.refund());
            assertEquals(Money.yen(Math.max(0, 12_000 - amount)), result.claim());
            assertEquals(amount > 12_000 ? 1 : 0, refunds.entries().size());
            assertEquals(amount < 12_000 ? 1 : 0, claims.entries().size());
            assertEquals(TransferImportResultCode.CANCELLED_SETTLED,
                imports.findByAccountDateAndInquiryNo(DEPARTURE.minusDays(30), "000001").orElseThrow().result());
            assertEquals(TransferImportResultCode.CANCELLED_SETTLED,
                imports.findByAccountDateAndInquiryNo(DEPARTURE.minusDays(30), "000002").orElseThrow().result());
            refunds.entries().forEach(refund -> refunds.rollbackRegistration(refund.reserveNo()));
            claims.entries().forEach(claim -> claims.rollbackRegistration(claim.reserveNo()));
        }
    }

    @Test
    @Tag("S-26-002/D-15001/8")
    @Tag("S-26-002/D-15001/10")
    @DisplayName("超過明細の全額を入金として返金し操作ログに記録する")
    void overpayment() {
        addImport("000001", Money.yen(35_000), TransferImportResultCode.OVERPAID);
        var result = cancel(DEPARTURE.minusDays(1));
        assertEquals(Money.yen(12_000), result.fee());
        assertEquals(Money.yen(35_000), result.paid());
        assertEquals(Money.yen(23_000), result.refund());
        assertEquals(Money.zero(), result.claim());
        assertEquals(result.refund(), refunds.entries().get(0).refundAmount());
        assertEquals(result.paid(), audit.entries().get(0).paid());
        assertEquals(result.fee(), audit.entries().get(0).fee());
        assertEquals(result.refund(), audit.entries().get(0).refund());
        assertEquals(result.claim(), audit.entries().get(0).claim());
        assertEquals(TransferImportResultCode.CANCELLED_SETTLED,
            imports.findByAccountDateAndInquiryNo(DEPARTURE.minusDays(30), "000001").orElseThrow().result());
    }

    @Test
    @Tag("S-26-002/D-15001/9")
    @DisplayName("振込済の予約では請求待ちを登録しない")
    void paid() {
        service.recordPayment("R1", DEPARTURE.minusDays(30), Money.yen(30_000));
        var result = cancel(DEPARTURE.minusDays(1));
        assertEquals(Money.yen(18_000), result.refund());
        assertEquals(0, claims.entries().size());
    }

    @Test
    @Tag("S-26-002/D-15003/4")
    @DisplayName("取消料も入金もないとき返金待ちと請求待ちを登録しない")
    void zeroFee() {
        var result = cancel(DEPARTURE.minusDays(21));
        assertEquals(Money.zero(), result.refund());
        assertEquals(Money.zero(), result.claim());
        assertEquals(0, refunds.entries().size());
        assertEquals(0, claims.entries().size());
    }

    @Test
    @DisplayName("操作ログの保存に失敗したら請求と明細と予約と残席を元に戻す")
    void rollsBackClaimAndMismatches() {
        addImport("000001", Money.yen(5_000), TransferImportResultCode.UNDERPAID);
        CancellationAuditRepository failingAudit = new CancellationAuditRepository() {
            public void record(CancellationAudit entry) {
                throw new IllegalStateException("記録失敗");
            }

            public void remove(CancellationAudit entry) {
            }
        };
        service = new ReservationService(tours, reservations, refunds, claims, imports, failingAudit);
        assertThrows(IllegalStateException.class, () -> cancel(DEPARTURE.minusDays(1)));
        assertEquals(0, claims.entries().size());
        assertEquals(TransferImportResultCode.UNDERPAID,
            imports.findByAccountDateAndInquiryNo(DEPARTURE.minusDays(30), "000001").orElseThrow().result());
        assertEquals(com.example.domain.TransferStatus.UNPAID, reservations.findByReserveNo("R1").orElseThrow().status());
        assertEquals(9, tours.findByCode("T001").orElseThrow().remainingSeats());
    }

    @Test
    @DisplayName("J110で不足の入金を取り込んだ後の取消でその入金を返金する")
    void importedUnderpaymentIsRefunded() {
        String number = "R000000000001";
        service.reserve(number, "T001", "M001", 1, 0, "", DEPARTURE.minusDays(30));
        LocalDate date = DEPARTURE.minusDays(30);
        BankTransferDetail detail = new BankTransferDetail("000003", date, date, Money.yen(20_000), number, "0", "");
        BankTransferFile file = new BankTransferFile(date, "1234567", List.of(detail), Money.yen(20_000));
        TransferImportService importer = new TransferImportService(
            reservations, imports, new InMemoryPaymentHandoffRepository(), new InMemoryPaymentAuditRepository());
        assertEquals(TransferImportResultCode.UNDERPAID, importer.importFile(file, "bank.dat").records().get(0).result());

        var result = service.cancel(number, "予定変更", DEPARTURE.minusDays(1),
            ReservationService.CancellationActor.customer("M001"));
        assertEquals(Money.yen(8_000), result.refund());
        assertEquals(Money.yen(8_000), refunds.entries().get(0).refundAmount());
        assertEquals(TransferImportResultCode.CANCELLED_SETTLED,
            imports.findByAccountDateAndInquiryNo(date, "000003").orElseThrow().result());
        var settledRecord = imports.findByAccountDateAndInquiryNo(date, "000003").orElseThrow();
        assertFalse(new TransferImportOutcome(List.of(settledRecord), List.of(), List.of(), false).hasExceptions());
    }

    private void addImport(String inquiryNo, Money amount, TransferImportResultCode code) {
        imports.save(new TransferImportRecord(DEPARTURE.minusDays(30), inquiryNo, amount, "payer", "R1", code, "test"));
    }

    private ReservationService.CancelResult cancel(LocalDate date) {
        return service.cancel("R1", "予定変更", date, ReservationService.CancellationActor.customer("M001"));
    }
}
