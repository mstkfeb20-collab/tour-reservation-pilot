package com.example.infrastructure;

import com.example.domain.TransferImportRecord;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

public class TransferCsvWriter {

    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.BASIC_ISO_DATE;
    private static final String HEADER = "勘定日,照会番号,振込依頼人名,金額,予約番号,区分";

    public void write(Path directory, List<TransferImportRecord> records) throws IOException {
        Files.createDirectories(directory);
        List<TransferImportRecord> mismatches = records.stream().filter(record -> record.result().isMismatch()).toList();
        List<TransferImportRecord> refunds = records.stream().filter(record -> record.result().isRefundTarget()).toList();
        writeFile(directory.resolve("mismatch.csv"), mismatches);
        writeFile(directory.resolve("refund.csv"), refunds);
    }

    private void writeFile(Path path, List<TransferImportRecord> records) throws IOException {
        String rows = records.stream()
            .map(record -> List.of(
                record.accountDate().format(DATE_FORMAT),
                record.inquiryNo(),
                record.payerName(),
                Long.toString(record.amount().toLong()),
                record.reserveNo() == null ? "" : record.reserveNo(),
                record.result().label()
            ).stream().map(this::escape).collect(Collectors.joining(",")))
            .collect(Collectors.joining("\r\n"));
        String content = "\uFEFF" + HEADER + "\r\n" + rows + (rows.isEmpty() ? "" : "\r\n");
        Files.writeString(path, content, StandardCharsets.UTF_8);
    }

    private String escape(String value) {
        if (value.contains(",") || value.contains("\"") || value.contains("\r") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
