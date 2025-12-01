plugins {
    kotlin("jvm") version "1.9.23"
}

group = "com.dabir"
version = "0.1.0"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
}
