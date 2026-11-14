/* Compile-only-layout experiment; this does not implement or run a native Server. */
#include "nativeweave_server_api_v1.h"
#include <stdio.h>
_Static_assert(sizeof(void *) == 8, "initial Server profile is 64-bit");
_Static_assert(sizeof(nw_server_dispatch_v1) == 32, "dispatch v1 size");
_Static_assert(offsetof(nw_server_dispatch_v1, on_control) == 24, "control callback offset");
_Static_assert(sizeof(nw_server_listener_v1) == 120, "listener v1 size");
_Static_assert(offsetof(nw_server_listener_v1, name) == 40, "listener text view offset");
_Static_assert(sizeof(nw_server_config_v1) == 136, "config v1 size");
_Static_assert(offsetof(nw_server_config_v1, listeners) == 104, "listener array offset");
_Static_assert(sizeof(nw_server_route_v1) == 112, "route v1 size");
_Static_assert(offsetof(nw_server_route_v1, protocol_descriptor) == 96, "protocol metadata offset");
_Static_assert(sizeof(nw_server_request_info_v1) == 240, "request metadata v1 size");
_Static_assert(offsetof(nw_server_request_info_v1, trace_context) == 176, "trace view offset");
_Static_assert(offsetof(nw_server_request_info_v1, cancellation_status) == 236, "cancel snapshot offset");
_Static_assert(sizeof(nw_server_snapshot_v1) == 80, "counter snapshot v1 size");
_Static_assert(sizeof(nw_server_close_result_v1) == 32, "close observation v1 size");
_Static_assert(sizeof(nw_server_sse_event_v1) == 72, "SSE v1 size");
typedef uint32_t (NW_CDECL *expected_dispatch_v1)(uintptr_t, uint64_t, uint64_t, uint32_t);
typedef uint32_t (NW_CDECL *expected_mcp_gate_v1)(nw_server_request *, uint32_t, nw_server_operation **, nw_error_info_v1 *);
typedef uint32_t (NW_CDECL *expected_grpc_metadata_v1)(nw_server_metadata *, nw_bytes_view_v1 *, nw_error_info_v1 *);
_Static_assert(_Generic(((nw_server_dispatch_v1 *)0)->on_request, expected_dispatch_v1: 1, default: 0), "phased dispatch signature");
_Static_assert(_Generic(&nw_server_mcp_gate_resume_create, expected_mcp_gate_v1: 1, default: 0), "MCP gate signature");
_Static_assert(_Generic(&nw_server_metadata_grpc_headers, expected_grpc_metadata_v1: 1, default: 0), "gRPC metadata projection signature");
int main(void) {
    puts("{\"scope\":\"design-C-layout-only\",\"pointer_bits\":64,\"assertions\":18,\"passed\":true}");
    return 0;
}
