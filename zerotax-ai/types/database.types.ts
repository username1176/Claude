export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          email: string;
          full_name: string | null;
          avatar_url: string | null;
          stripe_customer_id: string | null;
          subscription_tier: "free" | "premium" | "enterprise";
          subscription_status: "active" | "inactive" | "trialing" | "canceled";
          subscription_period_end: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          email: string;
          full_name?: string | null;
          avatar_url?: string | null;
          stripe_customer_id?: string | null;
          subscription_tier?: "free" | "premium" | "enterprise";
          subscription_status?: "active" | "inactive" | "trialing" | "canceled";
          subscription_period_end?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          email?: string;
          full_name?: string | null;
          avatar_url?: string | null;
          stripe_customer_id?: string | null;
          subscription_tier?: "free" | "premium" | "enterprise";
          subscription_status?: "active" | "inactive" | "trialing" | "canceled";
          subscription_period_end?: string | null;
          updated_at?: string;
        };
      };
      businesses: {
        Row: {
          id: string;
          user_id: string;
          name: string | null;
          is_active: boolean;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          name?: string | null;
          is_active?: boolean;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          name?: string | null;
          is_active?: boolean;
          updated_at?: string;
        };
      };
      questionnaire_responses: {
        Row: {
          id: string;
          business_id: string;
          user_id: string;
          business_stage: "idea" | "startup" | "growth" | "established" | "mature" | null;
          industry: string | null;
          entity_type_current: string | null;
          state_of_formation: string | null;
          states_operating: string[] | null;
          annual_revenue: number | null;
          annual_profit: number | null;
          w2_wages_paid: number | null;
          owner_draws: number | null;
          reasonable_salary: number | null;
          other_income: number | null;
          other_income_type: string | null;
          num_owners: number | null;
          married_filing_jointly: boolean | null;
          spouse_works: boolean | null;
          spouse_income: number | null;
          children_count: number | null;
          ages_children: number[] | null;
          family_in_business: boolean | null;
          real_estate_value: number | null;
          business_assets_value: number | null;
          investment_portfolio: number | null;
          retirement_accounts: number | null;
          total_net_worth: number | null;
          has_qsbs_stock: boolean | null;
          year_business_founded: number | null;
          goal_minimize_taxes: boolean | null;
          goal_asset_protection: boolean | null;
          goal_estate_planning: boolean | null;
          goal_exit_strategy: boolean | null;
          goal_retirement_planning: boolean | null;
          goal_hire_family: boolean | null;
          planning_horizon: "immediate" | "1_year" | "3_year" | "5_plus" | null;
          exit_timeline_years: number | null;
          additional_data: Json;
          completed_at: string | null;
          step_completed: number;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["questionnaire_responses"]["Row"],
          "id" | "created_at" | "updated_at"
        > & { id?: string; created_at?: string; updated_at?: string };
        Update: Partial<
          Omit<
            Database["public"]["Tables"]["questionnaire_responses"]["Row"],
            "id" | "created_at"
          >
        >;
      };
      recommendations: {
        Row: {
          id: string;
          business_id: string;
          user_id: string;
          questionnaire_id: string | null;
          title: string;
          executive_summary: string | null;
          recommended_entity_structure: string | null;
          entity_rationale: string | null;
          current_estimated_tax: number | null;
          optimized_estimated_tax: number | null;
          projected_annual_savings: number | null;
          projected_10yr_savings: number | null;
          savings_breakdown: Json | null;
          model_used: string;
          rag_chunks_used: number;
          raw_ai_response: string | null;
          status: "draft" | "complete" | "outdated" | "archived";
          law_version_date: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["recommendations"]["Row"],
          "id" | "created_at" | "updated_at"
        > & { id?: string; created_at?: string; updated_at?: string };
        Update: Partial<
          Omit<
            Database["public"]["Tables"]["recommendations"]["Row"],
            "id" | "created_at"
          >
        >;
      };
      strategies: {
        Row: {
          id: string;
          recommendation_id: string;
          user_id: string;
          category:
            | "entity_structure"
            | "retirement"
            | "depreciation"
            | "deductions"
            | "real_estate"
            | "estate_planning"
            | "asset_protection"
            | "exit"
            | "family_employment"
            | "qsbs"
            | "opportunity_zone"
            | "credits"
            | "state_tax";
          title: string;
          description: string;
          detailed_explanation: string | null;
          irc_sections: string[] | null;
          obbba_sections: string[] | null;
          state_law_refs: string[] | null;
          irs_publications: string[] | null;
          estimated_annual_savings: number | null;
          implementation_cost: number | null;
          payback_period_months: number | null;
          priority: "critical" | "high" | "medium" | "low";
          complexity: "simple" | "medium" | "complex" | "attorney_required";
          timeline_days: number | null;
          requires_attorney: boolean;
          requires_cpa: boolean;
          action_items: Json;
          user_status: "pending" | "in_progress" | "completed" | "skipped";
          completed_at: string | null;
          sort_order: number;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["strategies"]["Row"],
          "id" | "created_at" | "updated_at"
        > & { id?: string; created_at?: string; updated_at?: string };
        Update: Partial<
          Omit<Database["public"]["Tables"]["strategies"]["Row"], "id" | "created_at">
        >;
      };
      knowledge_base: {
        Row: {
          id: string;
          source_id: string | null;
          title: string;
          content: string;
          content_tokens: number | null;
          source_type:
            | "irs_publication"
            | "irc_section"
            | "obbba"
            | "revenue_ruling"
            | "tax_court"
            | "state_bulletin"
            | "treasury_reg"
            | "cca"
            | "plr";
          document_title: string | null;
          document_number: string | null;
          jurisdiction: string | null;
          effective_date: string | null;
          url: string | null;
          embedding: number[] | null;
          ingested_at: string;
          expires_at: string | null;
          created_at: string;
        };
        Insert: Omit<Database["public"]["Tables"]["knowledge_base"]["Row"], "id" | "created_at"> & {
          id?: string;
          created_at?: string;
        };
        Update: Partial<
          Omit<Database["public"]["Tables"]["knowledge_base"]["Row"], "id" | "created_at">
        >;
      };
      pdf_reports: {
        Row: {
          id: string;
          recommendation_id: string;
          user_id: string;
          storage_path: string;
          file_size_bytes: number | null;
          generated_at: string;
        };
        Insert: Omit<Database["public"]["Tables"]["pdf_reports"]["Row"], "id"> & { id?: string };
        Update: Partial<Database["public"]["Tables"]["pdf_reports"]["Row"]>;
      };
      subscriptions: {
        Row: {
          id: string;
          user_id: string;
          price_id: string;
          status: string;
          cancel_at_period_end: boolean;
          current_period_start: string | null;
          current_period_end: string | null;
          trial_end: string | null;
          metadata: Json;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<Database["public"]["Tables"]["subscriptions"]["Row"], "created_at" | "updated_at"> & {
          created_at?: string;
          updated_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["subscriptions"]["Row"]>;
      };
    };
    Views: Record<string, never>;
    Functions: {
      match_knowledge_base: {
        Args: {
          query_embedding: number[];
          match_threshold: number;
          match_count: number;
          filter_jurisdiction?: string;
        };
        Returns: Array<{
          id: string;
          title: string;
          content: string;
          source_type: string;
          document_title: string;
          document_number: string;
          jurisdiction: string;
          url: string;
          similarity: number;
        }>;
      };
    };
    Enums: Record<string, never>;
  };
}
