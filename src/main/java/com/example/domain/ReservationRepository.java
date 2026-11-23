package com.example.domain;

import java.util.Optional;

/** 予約の保存先。実装は infrastructure 層に置く。 */
public interface ReservationRepository {

    Optional<Reservation> findByReserveNo(String reserveNo);

    void save(Reservation reservation);
}
