package com.dabir.core.persistence

import com.dabir.core.model.Speaker
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import java.nio.file.Files

class FileSpeakerStoreTest {
    @Test
    fun `save and load speakers round trips data`() {
        val tempDir = Files.createTempDirectory("speakers-test")
        val path = tempDir.resolve("speakers.tsv")
        val store = FileSpeakerStore(path)

        val speakers = listOf(
            Speaker(id = "spk-1", displayName = "Alice", embeddings = floatArrayOf(0.1f, 0.2f), enrollmentClips = listOf("clip1.wav")),
            Speaker(id = "spk-2", displayName = "Bob", embeddings = null, enrollmentClips = emptyList())
        )

        store.save(speakers)
        val loaded = store.load()

        assertEquals(2, loaded.size)
        assertEquals(speakers[0].id, loaded[0].id)
        assertEquals(speakers[0].displayName, loaded[0].displayName)
        assertTrue(loaded[0].embeddings!!.contentEquals(speakers[0].embeddings!!))
        assertEquals(speakers[0].enrollmentClips, loaded[0].enrollmentClips)
        assertEquals(speakers[1].id, loaded[1].id)
        assertEquals(speakers[1].displayName, loaded[1].displayName)
        assertEquals(emptyList(), loaded[1].enrollmentClips)
    }
}
