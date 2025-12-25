/**
 * Zoom Controls Component.
 *
 * Provides zoom in/out controls for document viewing.
 *
 * Source: Design Document 10 - Visual Extraction Display
 * Verified: 2025-12-24
 */
import {
  Component,
  Input,
  Output,
  EventEmitter,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { SliderModule } from 'primeng/slider';
import { FormsModule } from '@angular/forms';
import { TooltipModule } from 'primeng/tooltip';

@Component({
  selector: 'app-zoom-controls',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonModule, SliderModule, TooltipModule],
  template: `
    <div class="zoom-controls">
      <p-button
        icon="pi pi-minus"
        [disabled]="zoomLevel <= minZoom"
        (onClick)="zoomOut()"
        styleClass="p-button-text p-button-sm"
        [pTooltip]="'Zoom out'"
      />

      <div class="zoom-slider">
        <p-slider
          [(ngModel)]="zoomLevel"
          [min]="minZoom"
          [max]="maxZoom"
          [step]="10"
          (onChange)="onSliderChange($event)"
        />
      </div>

      <span class="zoom-value">{{ zoomLevel }}%</span>

      <p-button
        icon="pi pi-plus"
        [disabled]="zoomLevel >= maxZoom"
        (onClick)="zoomIn()"
        styleClass="p-button-text p-button-sm"
        [pTooltip]="'Zoom in'"
      />

      <p-button
        icon="pi pi-refresh"
        (onClick)="resetZoom()"
        styleClass="p-button-text p-button-sm"
        [pTooltip]="'Reset zoom'"
      />
    </div>
  `,
  styles: [`
    .zoom-controls {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .zoom-slider {
      width: 100px;
    }

    .zoom-value {
      font-size: 0.875rem;
      color: #495057;
      min-width: 3rem;
      text-align: center;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ZoomControlsComponent {
  @Input() zoomLevel: number = 100;
  @Output() zoomChange = new EventEmitter<number>();

  readonly minZoom = 50;
  readonly maxZoom = 200;
  readonly step = 10;

  zoomIn(): void {
    const newZoom = Math.min(this.maxZoom, this.zoomLevel + this.step);
    this.emitZoomChange(newZoom);
  }

  zoomOut(): void {
    const newZoom = Math.max(this.minZoom, this.zoomLevel - this.step);
    this.emitZoomChange(newZoom);
  }

  resetZoom(): void {
    this.emitZoomChange(100);
  }

  onSliderChange(event: { value: number }): void {
    this.emitZoomChange(event.value);
  }

  private emitZoomChange(zoom: number): void {
    this.zoomChange.emit(zoom);
  }
}
