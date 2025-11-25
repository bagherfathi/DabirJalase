package com.meetingassistant.transport;

/**
 * Streaming client placeholder. Wire to gRPC stubs emitted by python_services.
 */
public class GrpcClient {
    public void initializeChannel() {
        // TODO: load channel config, TLS roots, and feature flags.
    }

    public void streamAudioChunk(byte[] payload) {
        throw new UnsupportedOperationException("Implement streaming to STT/diarization service.");
    }
}
