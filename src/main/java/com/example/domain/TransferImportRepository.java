package com.example.domain;

import java.time.LocalDate;
import java.util.Optional;

public interface TransferImportRepository {

    Optional<TransferImportRecord> findByAccountDateAndInquiryNo(LocalDate accountDate, String inquiryNo);

    void save(TransferImportRecord record);

    /** 予約の振込済更新と取込結果をまとめて保存し、版番号競合なら false を返す。 */
    boolean saveSettlement(
        Reservation reservation,
        long expectedVersion,
        boolean latePayment,
        TransferImportRecord record
    );

    boolean hasImportedFile(LocalDate creationDate, int detailCount, Money totalAmount);

    void saveFileSummary(LocalDate creationDate, int detailCount, Money totalAmount);
}
