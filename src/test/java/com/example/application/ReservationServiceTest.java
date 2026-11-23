package com.example.application;

import com.example.domain.Money;
import com.example.domain.Reservation;
import com.example.domain.Tour;
import com.example.domain.TransferStatus;
import com.example.infrastructure.InMemoryReservationRepository;
import com.example.infrastructure.InMemoryTourRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class ReservationServiceTest {

    static final LocalDate DEPARTURE = LocalDate.of(2027, 4, 30);

    InMemoryTourRepository tours;
    ReservationService service;

    @BeforeEach
    void setUp() {
        tours = new InMemoryTourRepository();
        tours.save(new Tour("T001", "春の京都 2日間", DEPARTURE, Money.yen(30_000), Money.yen(15_000), 10));
        service = new ReservationService(tours, new InMemoryReservationRepository());
    }

    int remainingSeats() {
        return tours.findByCode("T001").orElseThrow().remainingSeats();
    }

    @Nested
    @Tag("REQ-001")
    @DisplayName("REQ-001 予約の入力条件")
    class Reserve {

        LocalDate today = DEPARTURE.minusDays(30);

        @Test
        @DisplayName("条件を満たせば予約でき、合計金額が計算され、残席が人数分減る")
        void success() {
            Reservation r = service.reserve("R1", "T001", 2, 1, "窓側希望", today);
            assertEquals(Money.yen(75_000), r.sumPrice());
            assertEquals(TransferStatus.UNPAID, r.status());
            assertEquals(7, remainingSeats());
        }

        @Test
        @DisplayName("人数が0人なら予約できない")
        void zeroPeople() {
            assertThrows(IllegalArgumentException.class, () -> service.reserve("R1", "T001", 0, 0, "", today));
            assertEquals(10, remainingSeats());
        }

        @Test
        @DisplayName("子供のみでは予約できない")
        void childOnly() {
            assertThrows(IllegalArgumentException.class, () -> service.reserve("R1", "T001", 0, 2, "", today));
        }

        @Test
        @DisplayName("残席ちょうどまでは予約でき、超えると予約できない")
        void seats() {
            service.reserve("R1", "T001", 10, 0, "", today);
            assertEquals(0, remainingSeats());
            assertThrows(IllegalStateException.class, () -> service.reserve("R2", "T001", 1, 0, "", today));
        }

        @Test
        @DisplayName("出発日の7日前までは予約でき、6日前は予約できない")
        void deadline() {
            service.reserve("R1", "T001", 1, 0, "", DEPARTURE.minusDays(7));
            assertThrows(IllegalStateException.class, () -> service.reserve("R2", "T001", 1, 0, "", DEPARTURE.minusDays(6)));
        }

        @Test
        @DisplayName("備考は80文字まで入力でき、81文字は入力できない")
        void remarks() {
            service.reserve("R1", "T001", 1, 0, "あ".repeat(80), today);
            assertThrows(IllegalArgumentException.class, () -> service.reserve("R2", "T001", 1, 0, "あ".repeat(81), today));
        }
    }

    @Nested
    @Tag("REQ-002")
    @DisplayName("REQ-002 予約の取消")
    class Cancel {

        @BeforeEach
        void reserve() {
            service.reserve("R1", "T001", 2, 1, "", DEPARTURE.minusDays(30));
        }

        @Test
        @DisplayName("出発日の前日なら取り消せ、残席が戻る")
        void dayBefore() {
            service.cancel("R1", DEPARTURE.minusDays(1));
            assertEquals(10, remainingSeats());
        }

        @Test
        @DisplayName("出発日の当日は取り消せず、残席も変わらない")
        void departureDay() {
            assertThrows(IllegalStateException.class, () -> service.cancel("R1", DEPARTURE));
            assertEquals(7, remainingSeats());
        }

        @Test
        @DisplayName("取り消し済みの予約は再度取り消せない（残席が二重に戻らない）")
        void twice() {
            service.cancel("R1", DEPARTURE.minusDays(10));
            assertThrows(IllegalStateException.class, () -> service.cancel("R1", DEPARTURE.minusDays(10)));
            assertEquals(10, remainingSeats());
        }
    }

    @Nested
    @Tag("REQ-003")
    @DisplayName("REQ-003 取消料と返金額")
    class Fee {

        /** 合計 75,000円（大人 30,000×2 + 子供 15,000×1）を振込済にした予約を、出発 days 日前に取り消す。 */
        ReservationService.CancelResult cancelPaid(int days) {
            service.reserve("R1", "T001", 2, 1, "", DEPARTURE.minusDays(30));
            service.recordPayment("R1");
            return service.cancel("R1", DEPARTURE.minusDays(days));
        }

        @Test
        @DisplayName("21日前は0%")
        void day21() {
            ReservationService.CancelResult result = cancelPaid(21);
            assertEquals(Money.zero(), result.fee());
            assertEquals(Money.yen(75_000), result.refund());
        }

        @Test
        @DisplayName("20日前は20%")
        void day20() {
            assertEquals(Money.yen(15_000), cancelPaid(20).fee());
        }

        @Test
        @DisplayName("8日前は20%")
        void day8() {
            assertEquals(Money.yen(15_000), cancelPaid(8).fee());
        }

        @Test
        @DisplayName("7日前は30%")
        void day7() {
            assertEquals(Money.yen(22_500), cancelPaid(7).fee());
        }

        @Test
        @DisplayName("2日前は30%")
        void day2() {
            assertEquals(Money.yen(22_500), cancelPaid(2).fee());
        }

        @Test
        @DisplayName("前日は40%で、返金額は振込額から取消料を引いた額")
        void day1() {
            ReservationService.CancelResult result = cancelPaid(1);
            assertEquals(Money.yen(30_000), result.fee());
            assertEquals(Money.yen(45_000), result.refund());
        }

        @Test
        @DisplayName("未振込の予約は取消料を請求しない")
        void unpaid() {
            service.reserve("R1", "T001", 2, 1, "", DEPARTURE.minusDays(30));
            ReservationService.CancelResult result = service.cancel("R1", DEPARTURE.minusDays(1));
            assertEquals(Money.zero(), result.fee());
            assertEquals(Money.zero(), result.refund());
        }
    }
}
