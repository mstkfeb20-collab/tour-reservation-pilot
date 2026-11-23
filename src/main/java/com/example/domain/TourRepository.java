package com.example.domain;

import java.util.Optional;

/** ツアーの保存先。実装は infrastructure 層に置く。 */
public interface TourRepository {

    Optional<Tour> findByCode(String code);

    void save(Tour tour);
}
