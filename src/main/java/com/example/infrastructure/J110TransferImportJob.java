package com.example.infrastructure;

import com.example.application.TransferImportOutcome;
import com.example.application.TransferImportService;
import com.example.domain.BankTransferFile;

import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.LinkOption;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;

public class J110TransferImportJob {

    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.BASIC_ISO_DATE;

    private final Path inboundDirectory;
    private final Path archiveDirectory;
    private final Path reportDirectory;
    private final Path lockFile;
    private final If11FileParser parser;
    private final TransferImportService service;
    private final TransferCsvWriter csvWriter;

    public J110TransferImportJob(
        Path inboundDirectory,
        Path archiveDirectory,
        Path reportDirectory,
        Path lockFile,
        If11FileParser parser,
        TransferImportService service,
        TransferCsvWriter csvWriter
    ) {
        this.inboundDirectory = inboundDirectory;
        this.archiveDirectory = archiveDirectory;
        this.reportDirectory = reportDirectory;
        this.lockFile = lockFile.toAbsolutePath();
        this.parser = parser;
        this.service = service;
        this.csvWriter = csvWriter;
    }

    public JobResult run(LocalDate businessDate) {
        try {
            Files.createDirectories(lockFile.getParent());
            try (FileChannel channel = FileChannel.open(lockFile, StandardOpenOption.CREATE, StandardOpenOption.WRITE)) {
                FileLock lock;
                try {
                    lock = channel.tryLock();
                } catch (OverlappingFileLockException exception) {
                    return new JobResult(8, "J110はすでに実行中です", null);
                }
                if (lock == null) {
                    return new JobResult(8, "J110はすでに実行中です", null);
                }
                try (lock) {
                    return runLocked(businessDate);
                }
            }
        } catch (IOException | RuntimeException exception) {
            return new JobResult(8, exception.getMessage(), null);
        }
    }

    private JobResult runLocked(LocalDate businessDate) throws IOException {
        removeExpiredFiles(businessDate);
        List<Path> files;
        try (var entries = Files.list(inboundDirectory)) {
            files = entries.filter(path -> Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)).toList();
        }
        if (files.size() != 1) {
            return new JobResult(8, "受信フォルダには振込入金通知ファイルが1つだけ必要です", null);
        }

        Path filePath = files.get(0);
        BankTransferFile transferFile = parser.parse(Files.readAllBytes(filePath));
        TransferImportOutcome outcome = service.importFile(transferFile, filePath.getFileName().toString());
        if (!outcome.duplicateFile()) {
            csvWriter.write(reportDirectory.resolve(businessDate.format(DATE_FORMAT)), outcome.records());
        }
        Files.createDirectories(archiveDirectory);
        Path archivedFile = archiveDirectory.resolve(transferFile.creationDate().format(DATE_FORMAT) + "_" + filePath.getFileName());
        Files.move(filePath, archivedFile);
        int exitCode = outcome.hasExceptions() ? 4 : 0;
        return new JobResult(exitCode, "J110を終了しました", outcome);
    }

    private void removeExpiredFiles(LocalDate businessDate) throws IOException {
        LocalDate reportCutoff = businessDate.minusDays(90);
        if (Files.isDirectory(reportDirectory, LinkOption.NOFOLLOW_LINKS)) {
            try (var entries = Files.list(reportDirectory)) {
                for (Path directory : entries.filter(path -> Files.isDirectory(path, LinkOption.NOFOLLOW_LINKS)).toList()) {
                    LocalDate reportDate = datedName(directory.getFileName().toString());
                    if (reportDate != null && !reportDate.isAfter(reportCutoff)) {
                        Files.deleteIfExists(directory.resolve("mismatch.csv"));
                        Files.deleteIfExists(directory.resolve("refund.csv"));
                        try (var remaining = Files.list(directory)) {
                            if (remaining.findAny().isEmpty()) {
                                Files.deleteIfExists(directory);
                            }
                        }
                    }
                }
            }
        }

        LocalDate archiveCutoff = businessDate.minusMonths(13);
        if (Files.isDirectory(archiveDirectory, LinkOption.NOFOLLOW_LINKS)) {
            try (var entries = Files.list(archiveDirectory)) {
                for (Path file : entries.filter(path -> Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)).toList()) {
                    String name = file.getFileName().toString();
                    if (name.length() >= 9 && name.charAt(8) == '_') {
                        LocalDate archiveDate = datedName(name.substring(0, 8));
                        if (archiveDate != null && archiveDate.isBefore(archiveCutoff)) {
                            Files.deleteIfExists(file);
                        }
                    }
                }
            }
        }
    }

    private LocalDate datedName(String name) {
        try {
            return LocalDate.parse(name, DATE_FORMAT);
        } catch (DateTimeParseException exception) {
            return null;
        }
    }

    public record JobResult(int exitCode, String message, TransferImportOutcome outcome) {
    }
}
