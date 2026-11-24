package com.example.infrastructure;

import com.example.application.TransferImportService;
import com.example.domain.Money;
import com.example.domain.Reservation;
import com.example.domain.Tour;
import com.example.transfer.If11Fixtures;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

@Tag("REQ-23001")
@DisplayName("REQ-23001 J110振込取込")
class J110TransferImportJobTest {

    @TempDir
    Path tempDirectory;

    private Path inbound;
    private Path archive;
    private Path reports;
    private Path lockFile;
    private InMemoryReservationRepository reservations;
    private InMemoryTransferImportRepository imports;
    private J110TransferImportJob job;
    private Reservation reservation;

    @BeforeEach
    void setUp() throws IOException {
        inbound = Files.createDirectory(tempDirectory.resolve("inbound"));
        archive = tempDirectory.resolve("archive");
        reports = tempDirectory.resolve("reports");
        lockFile = tempDirectory.resolve("J110.lock");
        reservations = new InMemoryReservationRepository();
        imports = new InMemoryTransferImportRepository();
        InMemoryPaymentHandoffRepository handoffs = new InMemoryPaymentHandoffRepository();
        InMemoryPaymentAuditRepository audit = new InMemoryPaymentAuditRepository();
        reservation = Reservation.create(
            "R000000000001",
            new Tour("T0000001", "春の京都", LocalDate.of(2027, 4, 30), Money.yen(10_000), Money.yen(8_000), 10),
            1,
            0,
            "",
            LocalDate.of(2026, 4, 1)
        );
        reservations.save(reservation);
        job = new J110TransferImportJob(
            inbound,
            archive,
            reports,
            lockFile,
            new If11FileParser(),
            new TransferImportService(reservations, imports, handoffs, audit),
            new TransferCsvWriter()
        );
    }

    @Test
    @DisplayName("受信ファイルを消し込み、リストを出力して日付付きで退避する")
    void importsArchivesAndWritesReports() throws IOException {
        Files.write(inbound.resolve("bank.dat"), If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 10_000, reservation.reserveNo(), "0", "")
        )));

        J110TransferImportJob.JobResult result = job.run(LocalDate.of(2026, 4, 2));

        assertEquals(0, result.exitCode());
        assertEquals("1", reservation.status().code());
        assertTrue(Files.exists(archive.resolve("20260401_bank.dat")));
        assertTrue(Files.exists(reports.resolve("20260402/mismatch.csv")));
        assertTrue(Files.exists(reports.resolve("20260402/refund.csv")));
        assertFalse(Files.exists(inbound.resolve("bank.dat")));
    }

    @Test
    @DisplayName("形式エラーのファイルは終了コード8で終わり、予約を更新しない")
    void formatErrorDoesNotUpdateReservation() throws IOException {
        byte[] file = If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 10_000, reservation.reserveNo(), "0", "")
        ));
        file[411] = '9';
        Files.write(inbound.resolve("bank.dat"), file);

        J110TransferImportJob.JobResult result = job.run(LocalDate.of(2026, 4, 2));

        assertEquals(8, result.exitCode());
        assertEquals("0", reservation.status().code());
        assertTrue(imports.findByAccountDateAndInquiryNo(LocalDate.of(2026, 4, 1), "000001").isEmpty());
        assertTrue(Files.exists(inbound.resolve("bank.dat")));
    }

    @Test
    @DisplayName("不一致があるファイルは終了コード4で終わり不一致リストを出力する")
    void reportsMismatchWithWarningExitCode() throws IOException {
        Files.write(inbound.resolve("bank.dat"), If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 9_999, reservation.reserveNo(), "0", "")
        )));

        J110TransferImportJob.JobResult result = job.run(LocalDate.of(2026, 4, 2));

        assertEquals(4, result.exitCode());
        assertEquals("0", reservation.status().code());
        assertTrue(Files.readString(reports.resolve("20260402/mismatch.csv")).contains("不足"));
    }

    @Test
    @DisplayName("空明細は正常終了し、同じ作成日・件数・金額のファイルは再取込しない")
    void emptyAndDuplicateFiles() throws IOException {
        byte[] emptyFile = If11Fixtures.file(List.of());
        Files.write(inbound.resolve("empty.dat"), emptyFile);

        J110TransferImportJob.JobResult emptyResult = job.run(LocalDate.of(2026, 4, 2));
        assertEquals(0, emptyResult.exitCode());
        assertEquals(0, emptyResult.outcome().records().size());

        Files.write(inbound.resolve("resend.dat"), emptyFile);
        J110TransferImportJob.JobResult duplicateResult = job.run(LocalDate.of(2026, 4, 2));

        assertEquals(0, duplicateResult.exitCode());
        assertTrue(duplicateResult.outcome().duplicateFile());
        assertEquals(0, duplicateResult.outcome().records().size());
        assertTrue(Files.exists(archive.resolve("20260401_resend.dat")));
    }

    @Test
    @DisplayName("受信フォルダに複数ファイルがあれば何も消し込まず終了コード8にする")
    void requiresExactlyOneInputFile() throws IOException {
        byte[] file = If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 10_000, reservation.reserveNo(), "0", "")
        ));
        Files.write(inbound.resolve("one.dat"), file);
        Files.write(inbound.resolve("two.dat"), file);

        J110TransferImportJob.JobResult result = job.run(LocalDate.of(2026, 4, 2));

        assertEquals(8, result.exitCode());
        assertEquals("0", reservation.status().code());
    }

    @Test
    @DisplayName("同じロックファイルを保持中は多重起動を拒否する")
    void preventsConcurrentRuns() throws IOException {
        Files.write(inbound.resolve("bank.dat"), If11Fixtures.file(List.of(
            new If11Fixtures.Detail("000001", 10_000, reservation.reserveNo(), "0", "")
        )));

        try (FileChannel channel = FileChannel.open(lockFile, StandardOpenOption.CREATE, StandardOpenOption.WRITE);
             FileLock ignored = channel.lock()) {
            J110TransferImportJob.JobResult result = job.run(LocalDate.of(2026, 4, 2));
            assertEquals(8, result.exitCode());
            assertEquals("0", reservation.status().code());
        }
    }

    @Test
    @DisplayName("90日を過ぎたリストと13か月を過ぎた退避ファイルを削除する")
    void removesExpiredFiles() throws IOException {
        Path oldReports = Files.createDirectories(reports.resolve("20251001"));
        Files.writeString(oldReports.resolve("mismatch.csv"), "old");
        Files.writeString(oldReports.resolve("refund.csv"), "old");
        Files.createDirectories(archive);
        Files.writeString(archive.resolve("20250101_old.dat"), "old");
        Files.write(inbound.resolve("empty.dat"), If11Fixtures.file(List.of()));

        J110TransferImportJob.JobResult result = job.run(LocalDate.of(2026, 4, 2));

        assertEquals(0, result.exitCode());
        assertFalse(Files.exists(oldReports));
        assertFalse(Files.exists(archive.resolve("20250101_old.dat")));
    }
}
