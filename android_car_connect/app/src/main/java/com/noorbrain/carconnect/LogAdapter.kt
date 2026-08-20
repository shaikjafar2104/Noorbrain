package com.noorbrain.carconnect

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView

/**
 * LogAdapter
 *
 * Displays connection state log entries in a scrollable list.
 * Each entry is a single line from the connection log file.
 *
 * Designed for car-friendly readability: monospace font, dark background,
 * clear timestamps.
 */
class LogAdapter : ListAdapter<String, LogAdapter.LogViewHolder>(DiffCallback()) {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): LogViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_log_entry, parent, false)
        return LogViewHolder(view)
    }

    override fun onBindViewHolder(holder: LogViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    class LogViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        private val tvLogLine: TextView = view.findViewById(R.id.tv_log_line)

        fun bind(line: String) {
            tvLogLine.text = line
        }
    }

    class DiffCallback : DiffUtil.ItemCallback<String>() {
        override fun areItemsTheSame(oldItem: String, newItem: String): Boolean {
            return oldItem == newItem
        }

        override fun areContentsTheSame(oldItem: String, newItem: String): Boolean {
            return oldItem == newItem
        }
    }
}
