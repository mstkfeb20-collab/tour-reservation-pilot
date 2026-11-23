package com.example.infrastructure;

import com.example.domain.Money;
import com.example.domain.TransferImportRecord;
import com.example.domain.TransferImportResultCode;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;

@Tag("REQ-25001")
@DisplayName("REQ-25001 不一致リスト・返金対象リスト")
class TransferCsvWriterTest {

    @TempDir
    Path tempDirectory;

    @Test
    @DisplayName("不一致と返金対象を別々のUTF-8 BOM付きCSVに数字だけの金額で出力する()")
    void writesSeparateUtf8CsvFiles() throws Exception {
        TransferImportRecord mismatch = record("R000000000001", TransferImportResultCode.UNDERPAID, "ﾔﾏﾀﾞ,ﾀﾛｳ");
        TransferImportRecord refund = record("R000000000002", TransferImportResultCode.DUPLICATE_PAYMENT, "ｽｽﾞｷ");
        TransferCsvWriter writer = new TransferCsvWriter();

        writer.write(tempDirectory, List.of(mismatch, refund));

        byte[] mismatchBytes = Files.readAllBytes(tempDirectory.resolve("mismatch.csv"));
        String mismatchCsv = new String(mismatchBytes, StandardCharsets.UTF_8);
        String refundCsv = Files.readString(tempDirectory.resolve("refund.csv"), StandardCharsets.UTF_8);
        assertTrue(mismatchCsv.startsWith("\uFEFF勘定日,照会番号,振込依頼人名,金額,予約番号,区分\r\n"));
        assertTrue(mismatchCsv.contains("20260401,000001,\"ﾔﾏﾀﾞ,ﾀﾛｳ\",12345,R000000000001,不足"));
        assertTrue(refundCsv.contains("20260401,000001,ｽｽﾞｷ,12345,R000000000002,二重振込"));
        assertTrue(!refundCsv.contains("R000000000001"));
    }

    private static TransferImportRecord record(String reserveNo, TransferImportResultCode result, String payerName) {
        return new TransferImportRecord(
            LocalDate.of(2026, 4, 1),
            "000001",
            Money.yen(12_345),
            payerName,
            reserveNo,
            result,
            "bank.dat"
        );
    }
}
