/**
 * Page Navigator Component.
 *
 * Provides navigation controls for multi-page documents.
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
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputNumberModule } from 'primeng/inputnumber';
import { TooltipModule } from 'primeng/tooltip';

@Component({
  selector: 'app-page-navigator',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonModule, InputNumberModule, TooltipModule],
  template: `
    <div class="page-navigator">
      <p-button
        icon="pi pi-angle-double-left"
        [disabled]="currentPage <= 1"
        (onClick)="goToFirst()"
        styleClass="p-button-text p-button-sm"
        [pTooltip]="'First page'"
      />
      <p-button
        icon="pi pi-angle-left"
        [disabled]="currentPage <= 1"
        (onClick)="goToPrevious()"
        styleClass="p-button-text p-button-sm"
        [pTooltip]="'Previous page'"
      />

      <span class="page-info">
        Page
        <p-inputNumber
          [(ngModel)]="inputPage"
          [min]="1"
          [max]="totalPages"
          [showButtons]="false"
          [style]="{ width: '3rem' }"
          inputStyleClass="page-input"
          (onBlur)="onPageInputBlur()"
          (keydown.enter)="onPageInputBlur()"
        />
        of {{ totalPages }}
      </span>

      <p-button
        icon="pi pi-angle-right"
        [disabled]="currentPage >= totalPages"
        (onClick)="goToNext()"
        styleClass="p-button-text p-button-sm"
        [pTooltip]="'Next page'"
      />
      <p-button
        icon="pi pi-angle-double-right"
        [disabled]="currentPage >= totalPages"
        (onClick)="goToLast()"
        styleClass="p-button-text p-button-sm"
        [pTooltip]="'Last page'"
      />
    </div>
  `,
  styles: [`
    .page-navigator {
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .page-info {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
      color: #495057;
      margin: 0 0.5rem;
    }

    :host ::ng-deep .page-input {
      text-align: center;
      padding: 0.25rem;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PageNavigatorComponent {
  @Input() currentPage: number = 1;
  @Input() totalPages: number = 1;
  @Output() pageChange = new EventEmitter<number>();

  inputPage: number = 1;

  ngOnChanges(): void {
    this.inputPage = this.currentPage;
  }

  goToFirst(): void {
    this.emitPageChange(1);
  }

  goToPrevious(): void {
    if (this.currentPage > 1) {
      this.emitPageChange(this.currentPage - 1);
    }
  }

  goToNext(): void {
    if (this.currentPage < this.totalPages) {
      this.emitPageChange(this.currentPage + 1);
    }
  }

  goToLast(): void {
    this.emitPageChange(this.totalPages);
  }

  onPageInputBlur(): void {
    const page = Math.max(1, Math.min(this.totalPages, this.inputPage || 1));
    if (page !== this.currentPage) {
      this.emitPageChange(page);
    } else {
      this.inputPage = this.currentPage;
    }
  }

  private emitPageChange(page: number): void {
    this.inputPage = page;
    this.pageChange.emit(page);
  }
}
