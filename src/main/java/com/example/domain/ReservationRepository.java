package com.example.domain;

import java.time.LocalDate;
import java.util.Optional;

/** 予約の保存先。実装は infrastructure 層に置く。 */
public interface ReservationRepository {

    Optional<Reservation> findByReserveNo(String reserveNo);

    void save(Reservation reservation);

    default boolean saveCancellation(
        Reservation reservation,
        long expectedVersion,
        LocalDate cancelDate,
        String cancelReason
    ) {
        synchronized (reservation) {
            if (!reservation.cancel(expectedVersion, cancelDate, cancelReason)) {
                return false;
            }
            save(reservation);
            return true;
        }
    }
}
