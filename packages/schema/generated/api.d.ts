export interface paths {
    "/plans": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Plans */
        get: operations["list_plans_plans_get"];
        put?: never;
        /** Create Plan */
        post: operations["create_plan_plans_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Plan */
        get: operations["get_plan_plans__plan_id__get"];
        put?: never;
        post?: never;
        /** Delete Plan */
        delete: operations["delete_plan_plans__plan_id__delete"];
        options?: never;
        head?: never;
        /** Update Plan */
        patch: operations["update_plan_plans__plan_id__patch"];
        trace?: never;
    };
    "/plans/{plan_id}/solve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Solve Plan
         * @description Creates a new `ScenarioVersion` (status `pending`) and enqueues the
         *     real solve as an ARQ job (`coolblock_api.jobs.worker.run_plan_solve`).
         *     The job id is minted here (not left to ARQ to generate) so it can be
         *     handed back to the caller immediately -- the client opens
         *     `GET /plans/{plan_id}/scenarios/{version}/events?job_id=...` (Phase
         *     7's SSE endpoint) without a second round trip to discover it.
         */
        post: operations["solve_plan_plans__plan_id__solve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/scenarios": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Scenarios */
        get: operations["list_scenarios_plans__plan_id__scenarios_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/scenarios/{version}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Scenario */
        get: operations["get_scenario_plans__plan_id__scenarios__version__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/scenarios/{version}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Stream Scenario Events */
        get: operations["stream_scenario_events_plans__plan_id__scenarios__version__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/scenarios/{version}/export.geojson": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Scenario Geojson */
        get: operations["export_scenario_geojson_plans__plan_id__scenarios__version__export_geojson_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/scenarios/{version}/export.csv": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Export Scenario Csv */
        get: operations["export_scenario_csv_plans__plan_id__scenarios__version__export_csv_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/annotations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Annotations */
        get: operations["list_annotations_plans__plan_id__annotations_get"];
        put?: never;
        /** Create Annotation */
        post: operations["create_annotation_plans__plan_id__annotations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/annotations/{annotation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Annotation */
        delete: operations["delete_annotation_plans__plan_id__annotations__annotation_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/plans/{plan_id}/scenarios/{version}/share": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Share Link */
        post: operations["create_share_link_plans__plan_id__scenarios__version__share_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/share/{token}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Shared Scenario */
        get: operations["read_shared_scenario_share__token__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AnnotationCreate */
        AnnotationCreate: {
            /** Lng */
            lng: number;
            /** Lat */
            lat: number;
            /** Body */
            body: string;
        };
        /** AnnotationOut */
        AnnotationOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Plan Id
             * Format: uuid
             */
            plan_id: string;
            /** Author User Id */
            author_user_id: string;
            /** Lng */
            lng: number;
            /** Lat */
            lat: number;
            /** Body */
            body: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * ConstraintsIn
         * @description The E3 side-constraint surface (§6.5 E3), mirroring
         *     `engine.optimize.plan_service.SolveParams` minus `budget_usd` (which
         *     lives on the plan itself, not nested inside its constraints).
         */
        ConstraintsIn: {
            /**
             * Public Land Only
             * @default false
             */
            public_land_only: boolean;
            /** Max Sites Per Zone */
            max_sites_per_zone?: number | null;
            /** Min Spend Per Zone Usd */
            min_spend_per_zone_usd?: number | null;
            /** Annual Maintenance Cap Usd */
            annual_maintenance_cap_usd?: number | null;
            /** Mandatory Include Ids */
            mandatory_include_ids?: string[];
            /** Mandatory Exclude Ids */
            mandatory_exclude_ids?: string[];
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** PlanCreate */
        PlanCreate: {
            /** Name */
            name: string;
            /** Budget Usd */
            budget_usd: number;
            constraints?: components["schemas"]["ConstraintsIn"];
        };
        /** PlanOut */
        PlanOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Workspace Id */
            workspace_id: string;
            /** Name */
            name: string;
            /** Budget Usd */
            budget_usd: number;
            /** Constraints */
            constraints: {
                [key: string]: unknown;
            };
            /** Created By */
            created_by: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** PlanUpdate */
        PlanUpdate: {
            /** Name */
            name?: string | null;
            /** Budget Usd */
            budget_usd?: number | null;
            constraints?: components["schemas"]["ConstraintsIn"] | null;
        };
        /** ScenarioSiteOut */
        ScenarioSiteOut: {
            /** Rank */
            rank: number;
            /** Candidate Id */
            candidate_id: string;
            /** Intervention Type */
            intervention_type: string;
            /** Cost Usd */
            cost_usd: number;
            /** Marginal Gain Ewcb */
            marginal_gain_ewcb: number;
            /** Cumulative Ewcb */
            cumulative_ewcb: number;
            /** Cumulative Cost Usd */
            cumulative_cost_usd: number;
            /** Geometry */
            geometry: {
                [key: string]: unknown;
            };
            /** Properties */
            properties: {
                [key: string]: unknown;
            };
        };
        /**
         * ScenarioStatus
         * @enum {string}
         */
        ScenarioStatus: "pending" | "running" | "done" | "error";
        /** ScenarioVersionDetailOut */
        ScenarioVersionDetailOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Plan Id
             * Format: uuid
             */
            plan_id: string;
            /** Version Number */
            version_number: number;
            status: components["schemas"]["ScenarioStatus"];
            /** Solver */
            solver: string | null;
            /** Objective Value Ewcb */
            objective_value_ewcb: number | null;
            /** Cost Usd */
            cost_usd: number | null;
            /** Job Id */
            job_id: string | null;
            /** Error Message */
            error_message: string | null;
            /** Created By */
            created_by: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Completed At */
            completed_at: string | null;
            /** Sites */
            sites: components["schemas"]["ScenarioSiteOut"][];
        };
        /** ScenarioVersionOut */
        ScenarioVersionOut: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Plan Id
             * Format: uuid
             */
            plan_id: string;
            /** Version Number */
            version_number: number;
            status: components["schemas"]["ScenarioStatus"];
            /** Solver */
            solver: string | null;
            /** Objective Value Ewcb */
            objective_value_ewcb: number | null;
            /** Cost Usd */
            cost_usd: number | null;
            /** Job Id */
            job_id: string | null;
            /** Error Message */
            error_message: string | null;
            /** Created By */
            created_by: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Completed At */
            completed_at: string | null;
        };
        /** ShareLinkOut */
        ShareLinkOut: {
            /** Token */
            token: string;
            /**
             * Scenario Version Id
             * Format: uuid
             */
            scenario_version_id: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_plans_plans_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanOut"][];
                };
            };
        };
    };
    create_plan_plans_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_plan_plans__plan_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_plan_plans__plan_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_plan_plans__plan_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PlanUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PlanOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    solve_plan_plans__plan_id__solve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScenarioVersionOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_scenarios_plans__plan_id__scenarios_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScenarioVersionOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_scenario_plans__plan_id__scenarios__version__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
                version: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScenarioVersionDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stream_scenario_events_plans__plan_id__scenarios__version__events_get: {
        parameters: {
            query?: {
                after?: number;
            };
            header?: never;
            path: {
                plan_id: string;
                version: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_scenario_geojson_plans__plan_id__scenarios__version__export_geojson_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
                version: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    export_scenario_csv_plans__plan_id__scenarios__version__export_csv_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
                version: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_annotations_plans__plan_id__annotations_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnnotationOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_annotation_plans__plan_id__annotations_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AnnotationCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AnnotationOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_annotation_plans__plan_id__annotations__annotation_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
                annotation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_share_link_plans__plan_id__scenarios__version__share_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                plan_id: string;
                version: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ShareLinkOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_shared_scenario_share__token__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                token: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ScenarioVersionDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
}
