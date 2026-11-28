package com.example.infrastructure;

import com.example.domain.Money;
import com.example.domain.Reservation;
import com.example.domain.TransferImportRecord;
import com.example.domain.TransferImportRepository;
import com.example.domain.TransferImportResultCode;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryTransferImportRepository implements TransferImportRepository {

    private final Map<Key, TransferImportRecord> records = new ConcurrentHashMap<>();
    private final Set<FileKey> importedFiles = ConcurrentHashMap.newKeySet();

    @Override
    public Optional<TransferImportRecord> findByAccountDateAndInquiryNo(LocalDate accountDate, String inquiryNo) {
        return Optional.ofNullable(records.get(new Key(accountDate, inquiryNo)));
    }

    @Override
    public void save(TransferImportRecord record) {
        records.put(new Key(record.accountDate(), record.inquiryNo()), record);
    }

    @Override
    public List<TransferImportRecord> findMismatches(String reserveNo) {
        return records.values().stream()
            .filter(record -> reserveNo.equals(record.reserveNo()))
            .filter(record -> record.result() == TransferImportResultCode.UNDERPAID
                || record.result() == TransferImportResultCode.OVERPAID)
            .toList();
    }

    @Override
    public void settleMismatches(List<TransferImportRecord> mismatches) {
        for (TransferImportRecord record : mismatches) {
            save(new TransferImportRecord(record.accountDate(), record.inquiryNo(), record.amount(), record.payerName(),
                record.reserveNo(), TransferImportResultCode.CANCELLED_SETTLED, record.fileName()));
        }
    }

    @Override
    public void restoreMismatches(List<TransferImportRecord> mismatches) {
        mismatches.forEach(this::save);
    }

    @Override
    public boolean saveSettlement(
        Reservation reservation,
        long expectedVersion,
        boolean latePayment,
        TransferImportRecord record
    ) {
        synchronized (reservation) {
            try {
                reservation.markPaid(expectedVersion, record.accountDate(), record.amount(), latePayment);
            } catch (IllegalStateException exception) {
                return false;
            }
            records.put(new Key(record.accountDate(), record.inquiryNo()), record);
            return true;
        }
    }

    @Override
    public boolean hasImportedFile(LocalDate creationDate, int detailCount, Money totalAmount) {
        return importedFiles.contains(new FileKey(creationDate, detailCount, totalAmount));
    }

    @Override
    public void saveFileSummary(LocalDate creationDate, int detailCount, Money totalAmount) {
        importedFiles.add(new FileKey(creationDate, detailCount, totalAmount));
    }

    private record Key(LocalDate accountDate, String inquiryNo) {
    }

    private record FileKey(LocalDate creationDate, int detailCount, Money totalAmount) {
    }
}
