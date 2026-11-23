package com.example.infrastructure;

import com.example.domain.Reservation;
import com.example.domain.ReservationRepository;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/** 見本用のインメモリ実装。案件では DB の実装（RESERVE）に置き換える。 */
public class InMemoryReservationRepository implements ReservationRepository {

    private final Map<String, Reservation> store = new ConcurrentHashMap<>();

    @Override
    public Optional<Reservation> findByReserveNo(String reserveNo) {
        return Optional.ofNullable(store.get(reserveNo));
    }

    @Override
    public void save(Reservation reservation) {
        store.put(reservation.reserveNo(), reservation);
    }
}
