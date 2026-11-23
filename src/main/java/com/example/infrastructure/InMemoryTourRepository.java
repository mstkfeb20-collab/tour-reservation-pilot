package com.example.infrastructure;

import com.example.domain.Tour;
import com.example.domain.TourRepository;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/** 見本用のインメモリ実装。案件では DB の実装（TOURINFO）に置き換える。 */
public class InMemoryTourRepository implements TourRepository {

    private final Map<String, Tour> store = new ConcurrentHashMap<>();

    @Override
    public Optional<Tour> findByCode(String code) {
        return Optional.ofNullable(store.get(code));
    }

    @Override
    public void save(Tour tour) {
        store.put(tour.code(), tour);
    }
}
