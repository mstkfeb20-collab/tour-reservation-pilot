package com.example.application;

import com.example.domain.Money;
import com.example.domain.Tour;
import com.example.infrastructure.InMemoryCancellationAuditRepository;
import com.example.infrastructure.InMemoryClaimRepository;
import com.example.infrastructure.InMemoryRefundRepository;
import com.example.infrastructure.InMemoryReservationRepository;
import com.example.infrastructure.InMemoryTourRepository;
import com.example.infrastructure.InMemoryTransferImportRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

@Tag("REQ-21001")
@DisplayName("REQ-21001 取消理由の入力")
class CancellationReasonValidationTest {

    private static final LocalDate DEPARTURE = LocalDate.of(2027, 4, 30);
    private ReservationService service;

    @BeforeEach
    void setUp() {
        InMemoryTourRepository tours = new InMemoryTourRepository();
        tours.save(new Tour("T001", "春の京都", DEPARTURE, Money.yen(10_000), Money.yen(8_000), 5));
        service = new ReservationService(
            tours,
            new InMemoryReservationRepository(),
            new InMemoryRefundRepository(),
            new InMemoryClaimRepository(),
            new InMemoryTransferImportRepository(),
            new InMemoryCancellationAuditRepository()
        );
        service.reserve("R1", "T001", "M001", 1, 0, "", DEPARTURE.minusDays(30));
    }

    @Test
    @DisplayName("取消理由は1文字以上で必須")
    void reasonIsRequired() {
        IllegalArgumentException error = assertThrows(
            IllegalArgumentException.class,
            () -> cancel("")
        );

        assertEquals("取消理由を入力してください", error.getMessage());
    }

    @Test
    @DisplayName("全角・半角・改行を含む100文字の取消理由を受け付ける")
    void acceptsOneHundredCharactersAndNewlines() {
        String reason = ("あA\n").repeat(33) + "あ";

        service.cancel(
            "R1",
            reason,
            DEPARTURE.minusDays(1),
            ReservationService.CancellationActor.customer("M001")
        );
    }

    @Test
    @DisplayName("取消理由は100文字を超えられない")
    void rejectsMoreThanOneHundredCharacters() {
        IllegalArgumentException error = assertThrows(
            IllegalArgumentException.class,
            () -> cancel("あ".repeat(101))
        );

        assertEquals("取消理由は100文字以内で入力してください", error.getMessage());
    }

    private void cancel(String reason) {
        service.cancel(
            "R1",
            reason,
            DEPARTURE.minusDays(1),
            ReservationService.CancellationActor.customer("M001")
        );
    }
}
