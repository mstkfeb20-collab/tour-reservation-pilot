package com.example.architecture;

import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.library.Architectures.layeredArchitecture;

/**
 * 設計の境界を機械的に守る（docs/architecture.md）。
 * 失敗メッセージには「理由・修正・参照」を含め、エージェントが自分で直せるようにする。
 */
@DisplayName("アーキテクチャの境界")
class ArchitectureTest {

    private static JavaClasses classes;

    @BeforeAll
    static void importClasses() {
        classes = new ClassFileImporter()
            .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
            .importPackages("com.example");
    }

    @Test
    @DisplayName("ARCH-001 レイヤーの依存方向を守る")
    void layers() {
        layeredArchitecture()
            .consideringOnlyDependenciesInLayers()
            .layer("domain").definedBy("com.example.domain..")
            .layer("application").definedBy("com.example.application..")
            .layer("infrastructure").definedBy("com.example.infrastructure..")
            .whereLayer("application").mayOnlyBeAccessedByLayers("infrastructure")
            .whereLayer("infrastructure").mayNotBeAccessedByAnyLayer()
            .because("""

                理由: domain は他の層に依存してはいけません。依存方向が逆になると、業務ルールが技術の都合で変わります。
                修正: domain に interface を置き、実装を infrastructure に置いてください（依存性の逆転）。
                参照: docs/architecture.md#依存方向""")
            .check(classes);
    }

    @Test
    @DisplayName("ARCH-002 domain はフレームワークや入出力に依存しない")
    void domainIsPure() {
        noClasses().that().resideInAPackage("com.example.domain..")
            .should().dependOnClassesThat().resideInAnyPackage("java.sql..", "java.io..", "java.net..")
            .because("""

                理由: domain に入出力の都合が入ると、業務ルールをテストだけで確かめられなくなります。
                修正: 入出力は infrastructure に置き、domain には interface だけを置いてください。
                参照: docs/architecture.md#レイヤー""")
            .check(classes);
    }
}
