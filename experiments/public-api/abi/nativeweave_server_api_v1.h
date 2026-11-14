#ifndef NATIVEWEAVE_SERVER_API_V1_H
#define NATIVEWEAVE_SERVER_API_V1_H
/* Design-only Server domain ABI. Mirrors docs/api/server.md section 10. */
#include "nativeweave_api_v1.h"
#ifdef __cplusplus
extern "C" {
#endif

typedef struct nw_server nw_server;
typedef struct nw_server_request nw_server_request;
typedef struct nw_server_metadata nw_server_metadata;
typedef struct nw_server_buffer nw_server_buffer;
typedef struct nw_server_operation nw_server_operation;
typedef struct nw_server_managed_credit nw_server_managed_credit;
typedef struct nw_server_write_reservation nw_server_write_reservation;

typedef uint32_t (NW_CDECL *nw_server_on_request_v1)(
    uintptr_t cookie, uint64_t request_ticket, uint64_t handler_id);
typedef uint32_t (NW_CDECL *nw_server_on_control_v1)(
    uintptr_t cookie, uint32_t event_kind, uint32_t status,
    uint64_t request_ticket, const nw_error_info_v1 *borrowed_error);
typedef struct nw_server_dispatch_v1 {
    uint32_t struct_size, version; /* version = 1 */
    uintptr_t cookie;
    nw_server_on_request_v1 on_request;
    nw_server_on_control_v1 on_control; /* required; no user code inside callback */
} nw_server_dispatch_v1;

typedef struct nw_server_listener_v1 {
    uint32_t struct_size, version;
    uint32_t address_family, port; /* 4 or 6; 0..65535 */
    uint8_t address[16];           /* IPv4 in first four octets, remainder zero */
    uint32_t protocols, flags;     /* 1=http1,2=h2; flags bit0=tls,bit1=client-cert-required */
    nw_bytes_view_v1 name, certificate_chain_file, private_key_file, client_ca_file;
    uint64_t handshake_timeout_ns;
    uint32_t max_handshakes, reserved;
} nw_server_listener_v1;

typedef struct nw_server_config_v1 {
    uint32_t struct_size, version;
    uint64_t request_timeout_ns, shutdown_timeout_ns, header_timeout_ns, keepalive_ns;
    uint64_t max_request_bytes, managed_payload_bytes, native_payload_bytes, request_retained_bytes;
    uint32_t max_json_bytes, max_header_bytes, max_chunk_bytes, max_connections;
    uint32_t max_h2_streams, active_requests, queued_requests, listener_count;
    const nw_server_listener_v1 *listeners;
    nw_bytes_view_v1 trusted_proxies; /* bounded list encoding below */
    uint32_t forward_limit, reserved;
} nw_server_config_v1;

typedef struct nw_server_route_v1 {
    uint32_t struct_size, version;
    uint64_t handler_id;
    nw_bytes_view_v1 pattern, methods, endpoint_name;
    uint32_t kind, flags; /* kind 0=http,1=grpc,2=mcp; flags bit0=anonymous */
    uint64_t timeout_ns, max_request_bytes;
    uint32_t max_json_bytes, reserved;
    nw_bytes_view_v1 protocol_descriptor; /* empty HTTP; exact gRPC/MCP schema below */
} nw_server_route_v1;

typedef struct nw_server_request_info_v1 {
    uint32_t struct_size, version;
    uint64_t request_id, handler_id, remaining_timeout_ns;
    uint32_t kind, flags; /* flags bit0=content length present,bit1=TLS */
    uint64_t content_length;
    nw_bytes_view_v1 method, scheme, authority, path, raw_query;
    nw_bytes_view_v1 headers, route_values, query_values;
    nw_bytes_view_v1 trace_context, trace_state; /* empty or D19 32-byte v1 / bounded UTF-8 */
    uint32_t protocol, peer_family; /* protocol 1=http1,2=h2; peer 0=unknown,4,6 */
    uint8_t peer_address[16];
    uint32_t peer_port, cancellation_status; /* 0=no intent, NW_CANCELED or NW_TIMEOUT */
} nw_server_request_info_v1;

typedef struct nw_server_snapshot_v1 {
    uint32_t struct_size, version;
    uint32_t state, reserved; /* Native ServerState numeric values; reserved=0 */
    uint64_t active_requests, queued_requests, retiring_requests;
    uint64_t retained_managed_bytes, retained_native_bytes;
    uint64_t rejected_requests, callback_failures, diagnostic_drops;
} nw_server_snapshot_v1;

typedef struct nw_server_close_result_v1 {
    uint32_t struct_size, version;
    uint32_t close_status, pending_requests; /* 0=completed,1=pending; not nw_status */
    uint64_t retained_managed_bytes, retained_native_bytes;
} nw_server_close_result_v1;

typedef struct nw_server_sse_event_v1 {
    uint32_t struct_size, version;
    uint32_t present_flags, reserved; /* bit0=event,bit1=id,bit2=retry */
    nw_bytes_view_v1 data, event_name, id;
    uint64_t retry_milliseconds;
} nw_server_sse_event_v1;

uint32_t NW_CDECL nw_server_get_abi_v1(uint32_t requested_major, uint32_t out_capacity, nw_abi_info_v1 *out_info);
uint32_t NW_CDECL nw_server_create(const nw_server_config_v1 *, const nw_server_dispatch_v1 *, nw_server **out_server, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_routes_set(nw_server *, const nw_server_route_v1 *routes, uint32_t count, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_start_create(nw_server *, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_bound_addresses(nw_server *, nw_server_metadata **out_addresses, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_get_snapshot(nw_server *, nw_server_snapshot_v1 *out_snapshot, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_close_create(nw_server *, uint64_t wait_timeout_ns, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_tls_reload_create(nw_server *, nw_bytes_view_v1 listener_name, const nw_server_listener_v1 *tls_snapshot, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_try_retire(nw_server *); /* OK or PENDING; closes no new admission */
void NW_CDECL nw_server_release(nw_server *);

uint32_t NW_CDECL nw_server_operation_start(nw_server_operation *, const nw_operation_callbacks_v1 *, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_operation_request_cancel(nw_server_operation *);
uint32_t NW_CDECL nw_server_operation_take_void(nw_server_operation *, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_operation_take_write_reservation(nw_server_operation *, nw_server_write_reservation **out_reservation, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_operation_take_close(nw_server_operation *, nw_server_close_result_v1 *, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_operation_try_retire(nw_server_operation *);
void NW_CDECL nw_server_operation_release(nw_server_operation *);

uint32_t NW_CDECL nw_server_request_take(nw_server *, uint64_t ticket, nw_server_request **out_request, nw_server_metadata **out_metadata, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_metadata_read(nw_server_metadata *, nw_server_request_info_v1 *out_info, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_dispatch_complete(nw_server_request *, uint32_t application_status, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_request_abort(nw_server_request *);
uint32_t NW_CDECL nw_server_request_try_retire(nw_server_request *); /* OK or PENDING */
void NW_CDECL nw_server_metadata_release(nw_server_metadata *);
void NW_CDECL nw_server_request_release(nw_server_request *);

uint32_t NW_CDECL nw_server_managed_credit_acquire(nw_server_request *, uint64_t capacity, nw_server_managed_credit **out_credit, nw_error_info_v1 *);
void NW_CDECL nw_server_managed_credit_release(nw_server_managed_credit *);
uint32_t NW_CDECL nw_server_write_reserve_create(nw_server_request *, uint32_t kind, uint64_t native_capacity, nw_server_operation **out_op, nw_error_info_v1 *);
void NW_CDECL nw_server_write_reservation_release(nw_server_write_reservation *);

uint32_t NW_CDECL nw_server_body_read_create(nw_server_request *, uint32_t max_bytes, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_operation_take_chunk(nw_server_operation *, uint32_t *out_frame_kind, nw_server_buffer **out_buffer, nw_server_metadata **out_trailers, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_buffer_length(nw_server_buffer *, uint64_t *out_length, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_buffer_copy(nw_server_buffer *, uint8_t *destination, uint64_t capacity, uint64_t *out_written, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_buffer_managed_credit_acquire(nw_server_buffer *, uint64_t capacity, nw_server_managed_credit **out_credit, nw_error_info_v1 *);
void NW_CDECL nw_server_buffer_release(nw_server_buffer *);

uint32_t NW_CDECL nw_server_response_begin_create(nw_server_request *, uint32_t http_status, nw_bytes_view_v1 headers, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_response_write_create(nw_server_request *, nw_server_write_reservation *, nw_bytes_view_v1 bytes, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_response_flush_create(nw_server_request *, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_response_finish_create(nw_server_request *, nw_bytes_view_v1 trailers, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_sse_write_create(nw_server_request *, nw_server_write_reservation *, const nw_server_sse_event_v1 *, nw_server_operation **out_op, nw_error_info_v1 *);

uint32_t NW_CDECL nw_server_grpc_read_create(nw_server_request *, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_grpc_write_create(nw_server_request *, nw_server_write_reservation *, nw_bytes_view_v1 message, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_grpc_headers_create(nw_server_request *, nw_bytes_view_v1 metadata, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_grpc_status_create(nw_server_request *, uint32_t grpc_status, nw_bytes_view_v1 detail, nw_bytes_view_v1 trailers, nw_server_operation **out_op, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_mcp_call_take(nw_server_request *, uint32_t *out_call_kind, nw_server_buffer **out_arguments, nw_error_info_v1 *);
uint32_t NW_CDECL nw_server_mcp_reply_create(nw_server_request *, nw_server_write_reservation *, uint32_t reply_kind, nw_bytes_view_v1 result_json, nw_server_operation **out_op, nw_error_info_v1 *);

uint32_t NW_CDECL nw_server_metadata_headers(nw_server_metadata *, nw_bytes_view_v1 *out_headers, nw_error_info_v1 *);

#ifdef __cplusplus
}
#endif
#endif
