package com.example.domain;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

@Tag("REQ-002")
@DisplayName("REQ-002 振込状況は 未振込→振込済→取消 の順にしか進まない")
class ReservationTest {

    Reservation newReservation() {
        Tour tour = new Tour("T001", "春の京都 2日間", LocalDate.of(2027, 4, 30), Money.yen(30_000), Money.yen(15_000), 10);
        return Reservation.create("R1", tour, 1, 0, "");
    }

    @Test
    @DisplayName("未振込→振込済→取消 と進められる")
    void forward() {
        Reservation r = newReservation();
        r.markPaid();
        r.cancel();
        assertEquals(TransferStatus.CANCELLED, r.status());
    }

    @Test
    @DisplayName("取消から振込済には戻せない")
    void cancelledIsTerminal() {
        Reservation r = newReservation();
        r.cancel();
        assertThrows(IllegalStateException.class, r::markPaid);
    }

    @Test
    @DisplayName("区分値は既存システムと同じ 0・1・9")
    void codes() {
        assertEquals("0", TransferStatus.UNPAID.code());
        assertEquals("1", TransferStatus.PAID.code());
        assertEquals("9", TransferStatus.CANCELLED.code());
    }
}
